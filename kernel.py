import json
import os
import time
import datetime
import importlib
import sys
from pathlib import Path

# Auto-inject project root into python path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
    load_dotenv()  # also check cwd
except ImportError:
    pass

from boros.adapters import load_adapter
import subprocess

class BorosKernel:
    def __init__(self):
        self.boros_root = Path(__file__).parent
        self.registry = {}

        # Load config and manifest
        self._load_config()
        self._load_manifest()
        self._validate_world_model()
        self._check_first_boot()
        self._load_skills()


        # Initialize LLM providers (pass full config dict, not just provider string)
        try:
            self.evolution_llm = load_adapter(self.config["providers"]["evolution_api"])
            self.meta_eval_llm = load_adapter(self.config["providers"]["meta_eval_api"])

            # Force early initialization to ensure keys are valid
            if hasattr(self.evolution_llm, "client"):
                _ = self.evolution_llm.client
            if hasattr(self.meta_eval_llm, "client"):
                _ = self.meta_eval_llm.client

            print(f"Adapters loaded: evolution={self.config['providers']['evolution_api']['provider']}, meta_eval={self.config['providers']['meta_eval_api']['provider']}")
        except Exception as e:
            print(f"FATAL: Missing API Keys or Adapter Error: {e}")
            print("Please configure your .env file. Terminating entirely.")
            sys.exit(1)

    def _check_first_boot(self):
        boros_dir = self.boros_root
        session_dir = boros_dir / "session"
        cycle_file = session_dir / "current_cycle.json"

        if not cycle_file.exists():
            print("First boot detected. Initializing seed state...")
            session_dir.mkdir(parents=True, exist_ok=True)

            # Create directories
            dirs = [
                "tasks/queue", "tasks/active", "tasks/completed", "tasks/learning",
                "snapshots", "evals/scores", "commands",
                "memory/evolution_records", "memory/experiences",
                "memory/sessions", "memory"
            ]
            for d in dirs:
                (boros_dir / d).mkdir(parents=True, exist_ok=True)

            # Derive evals/categories.json from world_model.json
            categories = {}
            wm_path = boros_dir / "world_model.json"
            if wm_path.exists():
                try:
                    with open(wm_path) as f:
                        wm = json.load(f)
                    for cat_id, cat_data in wm.get("categories", {}).items():
                        categories[cat_id] = {
                            "name": cat_data.get("name", cat_id.replace("_", " ").title()),
                            "description": cat_data.get("description", "")
                        }
                except Exception as e:
                    print(f"Error loading world_model.json: {e}")

            with open(boros_dir / "evals" / "categories.json", "w") as f:
                json.dump(categories, f, indent=2)

            # Initialize high_water_marks.json
            high_water = {cat: 0.0 for cat in categories.keys()}
            hw_dir = boros_dir / "skills" / "eval-bridge" / "state"
            hw_dir.mkdir(parents=True, exist_ok=True)
            with open(hw_dir / "high_water_marks.json", "w") as f:
                json.dump(high_water, f, indent=2)

            # Initialize loop_state.json
            with open(session_dir / "loop_state.json", "w") as f:
                json.dump({
                    "cycle": 0,
                    "stage": None,
                    "mode": "evolution",
                    "cycle_started_at": None,
                    "total_cycles_completed": 0
                }, f, indent=2)

            # Create pending commands
            with open(boros_dir / "commands" / "pending.json", "w") as f:
                json.dump({"pending": []}, f)

            # Finish initialization mark
            with open(cycle_file, "w") as f:
                json.dump({"cycle": 0}, f)
            print("Seed state initialized successfully.")

        # ── Always sync world model → categories.json and high_water_marks.json ──
        self._sync_world_model_state(boros_dir)

    def _load_config(self):
        with open(self.boros_root / "config.json") as f:
            self.config = json.load(f)

    def _sync_world_model_state(self, boros_dir):
        """Sync categories.json and high_water_marks.json with current world_model.json.
        Runs on every boot to ensure new categories are always picked up."""
        wm_path = boros_dir / "world_model.json"
        if not wm_path.exists():
            return

        try:
            with open(wm_path) as f:
                wm = json.load(f)
            wm_categories = wm.get("categories", {})
            if not wm_categories:
                return

            # Sync categories.json
            cats_path = boros_dir / "evals" / "categories.json"
            cats_path.parent.mkdir(parents=True, exist_ok=True)
            categories = {}
            if cats_path.exists():
                try:
                    with open(cats_path) as f:
                        categories = json.load(f)
                except Exception:
                    categories = {}

            changed = False
            for cat_id, cat_data in wm_categories.items():
                if cat_id not in categories:
                    categories[cat_id] = {
                        "name": cat_data.get("name", cat_id.replace("_", " ").title()),
                        "description": cat_data.get("description", "")
                    }
                    changed = True

            # Remove categories no longer in world model
            for cat_id in list(categories.keys()):
                if cat_id not in wm_categories:
                    del categories[cat_id]
                    changed = True

            if changed:
                with open(cats_path, "w") as f:
                    json.dump(categories, f, indent=2)
                print(f"[Kernel] Synced categories.json with world_model.json ({len(categories)} categories)")

            # Sync high_water_marks.json
            hw_dir = boros_dir / "skills" / "eval-bridge" / "state"
            hw_dir.mkdir(parents=True, exist_ok=True)
            hw_path = hw_dir / "high_water_marks.json"

            high_water = {}
            if hw_path.exists():
                try:
                    with open(hw_path) as f:
                        high_water = json.load(f)
                except Exception:
                    high_water = {}

            hw_changed = False
            for cat_id in wm_categories:
                if cat_id not in high_water:
                    high_water[cat_id] = 0.0
                    hw_changed = True

            # Remove stale categories
            for cat_id in list(high_water.keys()):
                if cat_id not in wm_categories:
                    del high_water[cat_id]
                    hw_changed = True

            if hw_changed:
                with open(hw_path, "w") as f:
                    json.dump(high_water, f, indent=2)
                print(f"[Kernel] Synced high_water_marks.json with world_model.json")

        except Exception as e:
            print(f"[Kernel] Warning: World model sync failed: {e}")

    def _load_manifest(self):
        with open(self.boros_root / "manifest.json") as f:
            self.manifest = json.load(f)

    def _validate_world_model(self):
        """Ensure world_model.json has the required structure (FIX-04)."""
        wm_path = self.boros_root / "world_model.json"
        if not wm_path.exists():
            return
        
        try:
            with open(wm_path) as f:
                wm = json.load(f)

            assert "categories" in wm, "world_model.json must have 'categories' key"
            cats = wm["categories"]
            assert isinstance(cats, dict), "'categories' must be a dict"
            assert len(cats) > 0, "'categories' must have at least one category"

            for cat_id, cat_data in cats.items():
                required = ["weight", "anchors", "rubric", "failure_modes", "related_skills"]
                for field in required:
                    assert field in cat_data, f"Category '{cat_id}' missing required field '{field}'"
                assert isinstance(cat_data["related_skills"], list), f"'{cat_id}.related_skills' must be a list"
                assert cat_data["weight"] > 0, f"'{cat_id}.weight' must be positive"
        except AssertionError as e:
            print(f"[Kernel] FATAL ERROR: world_model.json validation failed: {e}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"[Kernel] FATAL ERROR: world_model.json is invalid JSON: {e}")
            sys.exit(1)

    def clock(self):
        return datetime.datetime.utcnow().isoformat() + "Z"

    def _load_skills(self):
        failed_skills = []
        for skill_name in self.manifest["skills"]:
            s_info = self.manifest["skills"][skill_name]
            try:
                module_path = f"boros.skills.{skill_name}.functions"
                module = importlib.import_module(module_path)
                for func_name in s_info.get("provided_functions", []):
                    if hasattr(module, func_name):
                        self.registry[func_name] = getattr(module, func_name)
                    else:
                        print(f"Warning: function {func_name} not found in {module_path}")
            except Exception as e:
                print(f"[KERNEL] WARNING: Failed to load skill '{skill_name}': {e}")
                failed_skills.append({"skill": skill_name, "error": str(e)})
                # Don't raise — continue loading other skills

        if failed_skills:
            print(f"[KERNEL] {len(failed_skills)} skills failed to load: {[s['skill'] for s in failed_skills]}")
            # Write failed skills to session for the agent to see
            try:
                session_dir = self.boros_root / "session"
                session_dir.mkdir(parents=True, exist_ok=True)
                with open(session_dir / "failed_skills.json", "w") as f:
                    json.dump(failed_skills, f, indent=2)
            except Exception:
                pass  # Don't let logging failure prevent boot

    def reload_skill(self, skill_name: str):
        print(f"[Kernel] Dynamically reloading skill: {skill_name}")
        s_info = self.manifest["skills"].get(skill_name)
        if not s_info:
            return False

        module_path = f"boros.skills.{skill_name}.functions"

        # 1. Reload specific function submodules to ensure fresh code
        for func_name in s_info.get("provided_functions", []):
            sub_path = f"{module_path}.{func_name}"
            if sub_path in sys.modules:
                importlib.reload(sys.modules[sub_path])

        # 2. Reload the main __init__ module to capture re-exported function pointers
        if module_path in sys.modules:
            module = importlib.reload(sys.modules[module_path])
        else:
            module = importlib.import_module(module_path)

        # 3. Re-bind fresh functions to registry
        for func_name in s_info.get("provided_functions", []):
            if hasattr(module, func_name):
                self.registry[func_name] = getattr(module, func_name)

        return True

if __name__ == "__main__":
    kernel = BorosKernel()
    import importlib
    interface_module = importlib.import_module("boros.skills.director-interface.functions.interface")
    ui = interface_module.DirectorInterface(kernel)
    ui.run()
