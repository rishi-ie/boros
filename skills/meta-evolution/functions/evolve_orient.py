
import os, json, glob, math

def evolve_orient(params: dict, kernel=None) -> dict:
    """Survey scores and identify the weakest skill categories. Returns orientation data
    filtered by world model related_skills mapping. Uses UCB1-inspired targeting to
    balance exploitation (fix weakest) with exploration (try untested skills)."""
    boros_dir = str(kernel.boros_root) if kernel else os.getcwd()

    # Load world model
    wm_path = os.path.join(boros_dir, "world_model.json")
    world_model = {}
    if os.path.exists(wm_path):
        try:
            with open(wm_path) as f:
                world_model = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    # Read high-water marks
    hw_file = os.path.join(boros_dir, "skills", "eval-bridge", "state", "high_water_marks.json")
    high_water = {}
    if os.path.exists(hw_file):
        try:
            with open(hw_file) as f:
                high_water = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    # Read latest eval scores
    results_dir = os.path.join(boros_dir, "eval-generator", "shared", "results")
    latest_scores = {}
    if os.path.isdir(results_dir):
        result_files = sorted(glob.glob(os.path.join(results_dir, "*.json")), key=os.path.getmtime, reverse=True)
        if result_files:
            try:
                with open(result_files[0]) as f:
                    latest_scores = json.load(f).get("scores", {})
            except (json.JSONDecodeError, OSError):
                pass

    # Identify weakest category using weighted score
    categories = world_model.get("categories", {})
    weakest_category = None
    weakest_score = float("inf")
    for cat_id, cat_data in categories.items():
        score = latest_scores.get(cat_id, high_water.get(cat_id, 0.0))
        weight = cat_data.get("weight", 1.0)
        # Weighted priority: lower score + higher weight = more urgent
        weighted_priority = score / weight if weight > 0 else score
        if weighted_priority < weakest_score:
            weakest_score = weighted_priority
            weakest_category = cat_id

    raw_weakest_score = latest_scores.get(weakest_category, high_water.get(weakest_category, 0.0)) if weakest_category else 0.0

    # Get related_skills for weakest category
    related_skills = []
    if weakest_category and weakest_category in categories:
        related_skills = categories[weakest_category].get("related_skills", [])

    # Read score history for trend analysis
    score_file = os.path.join(boros_dir, "memory", "score_history.jsonl")
    history = []
    if os.path.exists(score_file):
        try:
            with open(score_file) as f:
                for line in f:
                    if line.strip():
                        try:
                            history.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except OSError:
            pass

    # Read evolution records to count how many times each skill was targeted
    records_dir = os.path.join(boros_dir, "memory", "evolution_records")
    target_counts = {}  # skill_name -> times targeted
    recent_targets = []  # recently targeted files (for diversity)
    if os.path.isdir(records_dir):
        prop_files = sorted(glob.glob(os.path.join(records_dir, "prop-*.json")), key=os.path.getmtime, reverse=True)
        for rec in prop_files:
            try:
                with open(rec) as f:
                    prop = json.load(f)
                    target = prop.get("target", "")
                    target_file = prop.get("target_file", "").replace('\\', '/')
                    if target:
                        target_counts[target] = target_counts.get(target, 0) + 1
                    if target_file and len(recent_targets) < 5:
                        recent_targets.append(target_file)
            except (json.JSONDecodeError, OSError):
                pass
    recent_targets = list(dict.fromkeys(recent_targets))  # deduplicate preserving order

    # Read successful evolution records to identify which skills improved scores
    successful_skills = set()
    review_files = glob.glob(os.path.join(records_dir, "review-*.json")) if os.path.isdir(records_dir) else []
    for rfile in review_files:
        try:
            with open(rfile) as f:
                review = json.load(f)
            if review.get("verdict") == "apply":
                prop_id = review.get("proposal_id", "")
                prop_path = os.path.join(boros_dir, "session", "proposals", f"{prop_id}.json")
                if os.path.exists(prop_path):
                    with open(prop_path) as f2:
                        prop = json.load(f2)
                    successful_skills.add(prop.get("target", ""))
        except (json.JSONDecodeError, OSError):
            pass

    # Infrastructure skills that must never be evolution targets
    BANNED_SKILLS = {
        "eval-bridge", "loop-orchestrator", "meta-evaluation",
        "mode-controller", "context-orchestration", "skill-router"
    }

    # List all skill function files for targeting
    skills_dir = os.path.join(boros_dir, "skills")
    skill_targets = []
    total_cycles = len(history) + 1  # avoid log(0)

    if os.path.isdir(skills_dir):
        for skill_name in os.listdir(skills_dir):
            if skill_name in BANNED_SKILLS:
                continue
            func_dir = os.path.join(skills_dir, skill_name, "functions")
            if not os.path.isdir(func_dir):
                continue
            for py_file in glob.glob(os.path.join(func_dir, "*.py")):
                if os.path.basename(py_file) in ("__init__.py",) or py_file.endswith("__"):
                    continue
                size = os.path.getsize(py_file)
                is_related = skill_name in related_skills
                times_targeted = target_counts.get(skill_name, 0)
                has_succeeded = skill_name in successful_skills

                # UCB1-inspired priority score (lower = higher priority)
                # Base: normalized score gap from 1.0
                score_gap = 1.0 - raw_weakest_score
                # Exploration bonus: prefer less-targeted skills
                exploration = math.sqrt(2 * math.log(total_cycles + 1) / (times_targeted + 1))
                ucb_priority = score_gap - (exploration * 0.3)

                # Apply modifiers
                if is_related:
                    ucb_priority *= 0.3   # Strong boost for world-model-related skills
                if size < 150:
                    ucb_priority *= 0.7   # Prefer stubs (more room to improve)
                if has_succeeded:
                    ucb_priority *= 1.3   # Mild penalty: already improved, look elsewhere

                file_norm = py_file.replace('\\', '/')
                is_recent = any(
                    file_norm.endswith(rt.split('/')[-1])
                    for rt in recent_targets if rt
                )

                skill_targets.append({
                    "skill": skill_name,
                    "file": os.path.relpath(py_file, boros_dir).replace('\\', '/'),
                    "size_bytes": size,
                    "likely_stub": size < 150,
                    "related_to_weakest": is_related,
                    "times_targeted": times_targeted,
                    "recently_targeted": is_recent,
                    "priority_score": round(ucb_priority, 4)
                })

    # Filter out recently targeted files (force diversity)
    fresh_targets = [t for t in skill_targets if not t["recently_targeted"]]
    if not fresh_targets:
        fresh_targets = skill_targets  # all were recent, use all

    # FIX-06: Filter out blocked files (anti-brute-force)
    try:
        import importlib.util
        _lp = os.path.join(boros_dir, "skills", "meta-evolution", "functions", "_internal", "evolution_ledger.py")
        _sp = importlib.util.spec_from_file_location("evolution_ledger", _lp)
        ledger = importlib.util.module_from_spec(_sp)
        _sp.loader.exec_module(ledger)
        unblocked = []
        for t in fresh_targets:
            if not ledger.check_brute_force(boros_dir, t["file"]):
                unblocked.append(t)
        if unblocked:
            fresh_targets = unblocked
    except Exception:
        pass

    # Sort by priority score
    fresh_targets.sort(key=lambda x: x["priority_score"])

    # Separate related vs general candidates
    related_candidates = [t for t in fresh_targets if t["related_to_weakest"]]
    general_candidates = [t for t in fresh_targets if not t["related_to_weakest"]]

    # Prefer related candidates; fall back to general if not enough
    if len(related_candidates) >= 2:
        candidates = related_candidates[:8]
    elif related_candidates:
        candidates = related_candidates + general_candidates[:5]
    else:
        candidates = general_candidates[:8]

    if weakest_score == float("inf"):
        weakest_score = 999.0

    # FIX-08: Activate Knowledge Graph (query history for candidates)
    kg_data = []
    if kernel and "memory_kg_query" in kernel.registry and related_skills:
        try:
            for rs in related_skills:
                res = kernel.registry["memory_kg_query"]({
                    "subject": rs, 
                    "predicate": "was_modified", 
                    "include_history": True
                }, kernel)
                if res and res.get("status") == "ok":
                    kg_data.extend(res.get("results", []))
        except Exception as e:
            print(f"[evolve_orient] WARNING: KG query failed: {e}")

    return {
        "status": "ok",
        "weakest_category": weakest_category,
        "weakest_score": round(raw_weakest_score, 3),
        "related_skills": related_skills,
        "high_water_marks": high_water,
        "latest_scores": latest_scores,
        "history_entries": len(history),
        "candidates": candidates[:10],
        "kg_history": kg_data,
        "total_skill_files": len(skill_targets),
        "recommendation": (
            f"Weakest category: '{weakest_category}' (score: {raw_weakest_score:.3f}). "
            f"Related skills to target: {related_skills}. "
            f"Top candidate: {candidates[0]['file'] if candidates else 'none'}. "
            f"Targeting uses UCB1 exploration — prefers related, understubbed, rarely-targeted files. "
            f"Blocked files were filtered out automatically."
        )
    }
