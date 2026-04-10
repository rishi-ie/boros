"""
Boros Adaptation Engine

Runs on a configured schedule (or manually via 'boros adapt') in boros-fork state.
Analyzes real task execution logs to propose behavioral improvements, sends them
through a lightweight review board, then applies approved changes to SKILL.md files,
skill code, and world model weights.

This is fundamentally different from ARES evolution:
- ARES evolves against a synthetic eval rubric (self-improvement pressure)
- AdaptEngine evolves against real usage patterns (environmental pressure)
- No rollback system needed — changes are smaller in scope and reviewed
"""

import json
import datetime
import traceback
from pathlib import Path


class AdaptEngine:
    def __init__(self, kernel, log_callback=None):
        self.kernel = kernel
        self.boros_root = kernel.boros_root
        self.log = log_callback or print

    def run(self):
        """Run one adaptation cycle. Returns True if changes were applied."""
        self.log("[ADAPT] Starting adaptation cycle...")

        config = self._load_config()
        min_tasks = config.get("fork", {}).get("min_tasks_before_adapt", 10)

        tasks = self._load_tasks_since_last_adapt(config)

        if len(tasks) < min_tasks:
            self.log(f"[ADAPT] Not enough tasks ({len(tasks)}/{min_tasks}) since last adaptation. Skipping.")
            return False

        self.log(f"[ADAPT] Analyzing {len(tasks)} tasks...")

        wm = self._load_world_model()
        skill_names = self._get_skills_with_skill_md()
        skill_mds = self._load_skill_mds(skill_names)

        proposed = self._propose_changes(tasks, skill_mds, wm)
        if not proposed:
            self.log("[ADAPT] LLM proposal failed. Aborting.")
            return False

        analysis = proposed.get("analysis", "")
        changes = proposed.get("proposed_changes", [])
        self.log(f"[ADAPT] Analysis: {analysis}")

        if not changes:
            self.log("[ADAPT] No changes proposed.")
            self._update_last_adapt_timestamp()
            return False

        self.log(f"[ADAPT] {len(changes)} change(s) proposed. Sending to review board...")

        decision = self._review_changes(analysis, changes)
        outcome = decision.get("decision", "rejected")
        reason = decision.get("reason", "")

        if outcome != "approved":
            self.log(f"[ADAPT] Review board rejected: {reason}")
            self._log_adapt_event(tasks, analysis, changes, "rejected", reason)
            self._update_last_adapt_timestamp()
            return False

        self.log(f"[ADAPT] Approved: {reason}. Applying...")

        applied = self._apply_changes(changes)
        self.log(f"[ADAPT] Applied {applied}/{len(changes)} change(s).")
        self._log_adapt_event(tasks, analysis, changes, "applied", reason)
        self._update_last_adapt_timestamp()
        return applied > 0

    # ─────────────────────────────────────────────
    # Data loading
    # ─────────────────────────────────────────────

    def _load_config(self):
        return json.loads((self.boros_root / "config.json").read_text(encoding="utf-8"))

    def _load_world_model(self):
        wm_path = self.boros_root / "world_model.json"
        if not wm_path.exists():
            return {}
        return json.loads(wm_path.read_text(encoding="utf-8"))

    def _load_tasks_since_last_adapt(self, config):
        last_ts = config.get("fork", {}).get("last_adapt_timestamp")
        task_log = self.boros_root / "logs" / "task_log.jsonl"
        if not task_log.exists():
            return []

        tasks = []
        for line in task_log.read_text(encoding="utf-8").strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if last_ts and entry.get("timestamp", "") <= last_ts:
                    continue
                tasks.append(entry)
            except Exception:
                pass
        return tasks

    def _get_skills_with_skill_md(self):
        manifest_path = self.boros_root / "manifest.json"
        if not manifest_path.exists():
            return []
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return [
            name for name in manifest.get("skills", {})
            if (self.boros_root / "skills" / name / "SKILL.md").exists()
        ]

    def _load_skill_mds(self, skill_names):
        skill_mds = {}
        for name in skill_names:
            path = self.boros_root / "skills" / name / "SKILL.md"
            if path.exists():
                try:
                    skill_mds[name] = path.read_text(encoding="utf-8")
                except Exception:
                    pass
        return skill_mds

    # ─────────────────────────────────────────────
    # LLM calls
    # ─────────────────────────────────────────────

    def _propose_changes(self, tasks, skill_mds, world_model):
        """Ask evolution_api to analyze task data and propose behavioral changes."""
        total = len(tasks)
        failed = sum(1 for t in tasks if t.get("status") not in ("completed",))
        high_retry = sum(1 for t in tasks if t.get("empty_turns", 0) > 1)

        recent_detail = json.dumps(tasks[-20:], indent=2)

        skills_section = ""
        for name, md in skill_mds.items():
            skills_section += f"\n### '{name}' SKILL.md (first 600 chars):\n{md[:600]}\n"

        weights = {
            k: v.get("weight")
            for k, v in world_model.get("categories", {}).items()
        }

        prompt = (
            "You are the Boros Adaptation Engine. Analyze task execution logs and propose "
            "behavioral improvements grounded in the actual data.\n\n"
            f"TASK STATISTICS (since last adaptation):\n"
            f"- Total tasks: {total}\n"
            f"- Failed/errored: {failed} ({round(failed / max(total, 1) * 100)}%)\n"
            f"- High-retry tasks (empty_turns > 1): {high_retry} ({round(high_retry / max(total, 1) * 100)}%)\n\n"
            f"RECENT TASK LOG (last 20):\n{recent_detail}\n\n"
            f"CURRENT SKILL DEFINITIONS:{skills_section}\n"
            f"CURRENT WORLD MODEL WEIGHTS:\n{json.dumps(weights, indent=2)}\n\n"
            "Propose specific behavioral improvements. Only propose changes you can directly "
            "justify with data from the task log.\n\n"
            "Return raw JSON only — no markdown fences:\n"
            "{\n"
            '  "analysis": "2-3 sentence summary of key patterns",\n'
            '  "proposed_changes": [\n'
            "    {\n"
            '      "type": "skill_md",\n'
            '      "skill_name": "<skill-folder-name>",\n'
            '      "old_text": "<exact text to find in SKILL.md>",\n'
            '      "new_text": "<replacement text>",\n'
            '      "reason": "<specific data point from the log>"\n'
            "    },\n"
            "    {\n"
            '      "type": "world_model_weight",\n'
            '      "category": "<category_id>",\n'
            '      "new_weight": <number>,\n'
            '      "reason": "<why>"\n'
            "    },\n"
            "    {\n"
            '      "type": "skill_code",\n'
            '      "target_file": "<relative path from boros root>",\n'
            '      "old_text": "<exact text to find>",\n'
            '      "new_text": "<replacement>",\n'
            '      "reason": "<specific data point>"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "If no changes are warranted: {\"analysis\": \"...\", \"proposed_changes\": []}"
        )

        try:
            response = self.kernel.evolution_llm.complete(
                [{"role": "user", "content": prompt}],
                system="You are an AI adaptation engine. Return only valid JSON, no markdown."
            )
            for block in response.get("content", []):
                if block.get("type") == "text":
                    text = block["text"].strip()
                    # Strip markdown fences if model ignores the instruction
                    if text.startswith("```"):
                        parts = text.split("```")
                        text = parts[1] if len(parts) > 1 else text
                        if text.startswith("json"):
                            text = text[4:]
                    return json.loads(text.strip())
        except Exception as e:
            self.log(f"[ADAPT] Proposal LLM call failed: {e}")
        return None

    def _review_changes(self, analysis, changes):
        """Lightweight review: approve or reject the proposed batch."""
        prompt = (
            "You are reviewing proposed behavioral adaptations for a deployed AI agent.\n\n"
            f"ANALYSIS:\n{analysis}\n\n"
            f"PROPOSED CHANGES:\n{json.dumps(changes, indent=2)}\n\n"
            "Approve if: changes are grounded in actual usage data, genuinely improve performance, "
            "and skill_code changes are minimal and safe.\n"
            "Reject if: changes are speculative, harmful, or not supported by the data.\n\n"
            "Return raw JSON only:\n"
            "{\"decision\": \"approved\" or \"rejected\", \"reason\": \"one sentence\"}"
        )

        try:
            response = self.kernel.meta_eval_llm.complete(
                [{"role": "user", "content": prompt}],
                system="You are a strict review board. Return only valid JSON."
            )
            for block in response.get("content", []):
                if block.get("type") == "text":
                    text = block["text"].strip()
                    if text.startswith("```"):
                        parts = text.split("```")
                        text = parts[1] if len(parts) > 1 else text
                        if text.startswith("json"):
                            text = text[4:]
                    return json.loads(text.strip())
        except Exception as e:
            self.log(f"[ADAPT] Review LLM call failed: {e}")
        return {"decision": "rejected", "reason": "Review call failed"}

    # ─────────────────────────────────────────────
    # Apply changes
    # ─────────────────────────────────────────────

    def _apply_changes(self, changes):
        applied = 0
        for change in changes:
            try:
                ctype = change.get("type")

                if ctype == "skill_md":
                    applied += self._apply_skill_md(change)

                elif ctype == "world_model_weight":
                    applied += self._apply_world_model_weight(change)

                elif ctype == "skill_code":
                    applied += self._apply_skill_code(change)

                else:
                    self.log(f"[ADAPT] Unknown change type: {ctype}")

            except Exception as e:
                self.log(f"[ADAPT] Failed to apply change ({change.get('type')}): {e}")
                self.log(traceback.format_exc())

        return applied

    def _apply_skill_md(self, change):
        skill_name = change.get("skill_name", "")
        old_text = change.get("old_text", "")
        new_text = change.get("new_text", "")
        skill_md_path = self.boros_root / "skills" / skill_name / "SKILL.md"

        if not skill_md_path.exists():
            self.log(f"[ADAPT] SKILL.md not found: skills/{skill_name}/SKILL.md")
            return 0
        content = skill_md_path.read_text(encoding="utf-8")
        if old_text not in content:
            self.log(f"[ADAPT] old_text not found in {skill_name}/SKILL.md — skipping")
            return 0

        skill_md_path.write_text(content.replace(old_text, new_text, 1), encoding="utf-8")
        self.log(f"[ADAPT] Updated SKILL.md: {skill_name} — {change.get('reason', '')}")
        return 1

    def _apply_world_model_weight(self, change):
        category = change.get("category", "")
        try:
            new_weight = float(change.get("new_weight", 0))
        except (TypeError, ValueError):
            self.log(f"[ADAPT] Invalid weight value for {category}")
            return 0

        wm_path = self.boros_root / "world_model.json"
        wm = json.loads(wm_path.read_text(encoding="utf-8"))
        if category not in wm.get("categories", {}):
            self.log(f"[ADAPT] Category not in world model: {category}")
            return 0

        old_weight = wm["categories"][category].get("weight", "?")
        wm["categories"][category]["weight"] = new_weight
        wm_path.write_text(json.dumps(wm, indent=2), encoding="utf-8")
        self.log(f"[ADAPT] World model weight: {category} {old_weight} → {new_weight}")
        return 1

    def _apply_skill_code(self, change):
        target_file = change.get("target_file", "")
        old_text = change.get("old_text", "")
        new_text = change.get("new_text", "")
        file_path = self.boros_root / target_file

        if not file_path.exists():
            self.log(f"[ADAPT] Target file not found: {target_file}")
            return 0
        content = file_path.read_text(encoding="utf-8")
        if old_text not in content:
            self.log(f"[ADAPT] old_text not found in {target_file} — skipping")
            return 0

        file_path.write_text(content.replace(old_text, new_text, 1), encoding="utf-8")
        self.log(f"[ADAPT] Updated skill code: {target_file}")

        # Hot-reload the affected skill
        parts = Path(target_file).parts
        if len(parts) >= 2 and parts[0] == "skills":
            skill_name = parts[1]
            try:
                self.kernel.reload_skill(skill_name)
                self.log(f"[ADAPT] Hot-reloaded: {skill_name}")
            except Exception as e:
                self.log(f"[ADAPT] Hot-reload failed for {skill_name}: {e}")

        return 1

    # ─────────────────────────────────────────────
    # State persistence
    # ─────────────────────────────────────────────

    def _update_last_adapt_timestamp(self):
        config_path = self.boros_root / "config.json"
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            if "fork" not in config:
                config["fork"] = {}
            config["fork"]["last_adapt_timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
            config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        except Exception as e:
            self.log(f"[ADAPT] Failed to update timestamp: {e}")

    def _log_adapt_event(self, tasks, analysis, changes, outcome, reason):
        adapt_log = self.boros_root / "logs" / "adapt_log.jsonl"
        adapt_log.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "tasks_analyzed": len(tasks),
            "analysis": analysis,
            "changes_proposed": len(changes),
            "outcome": outcome,
            "reason": reason,
            "changes": changes
        }
        with open(adapt_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
