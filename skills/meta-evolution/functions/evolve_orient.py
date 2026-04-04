
import os, json, glob
def evolve_orient(params: dict, kernel=None) -> dict:
    """Survey scores and identify weakest skill categories. Returns orientation data
    filtered by world model related_skills mapping."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"

    # Load world model for category→skill mapping
    wm_path = os.path.join(boros_dir, "world_model.json")
    world_model = {}
    if os.path.exists(wm_path):
        with open(wm_path) as f:
            world_model = json.load(f)

    # Read high-water marks
    hw_file = os.path.join(boros_dir, "skills", "eval-bridge", "state", "high_water_marks.json")
    high_water = {}
    if os.path.exists(hw_file):
        with open(hw_file) as f:
            high_water = json.load(f)

    # Read latest eval scores
    results_dir = os.path.join(boros_dir, "eval-generator", "shared", "results")
    latest_scores = {}
    if os.path.isdir(results_dir):
        result_files = sorted(glob.glob(os.path.join(results_dir, "*.json")), key=os.path.getmtime, reverse=True)
        if result_files:
            try:
                with open(result_files[0]) as f:
                    latest_scores = json.load(f).get("scores", {})
            except Exception:
                pass

    # Identify weakest category
    categories = world_model.get("categories", {})
    weakest_category = None
    weakest_score = float("inf")
    for cat_id in categories:
        score = latest_scores.get(cat_id, high_water.get(cat_id, 0.0))
        if score < weakest_score:
            weakest_score = score
            weakest_category = cat_id

    # Get related_skills for weakest category from world model
    related_skills = []
    if weakest_category and weakest_category in categories:
        related_skills = categories[weakest_category].get("related_skills", [])

    # Read score history for trend
    score_file = os.path.join(boros_dir, "memory", "score_history.jsonl")
    history = []
    if os.path.exists(score_file):
        with open(score_file) as f:
            for line in f:
                if line.strip():
                    try:
                        history.append(json.loads(line))
                    except Exception:
                        pass

    # List all skill function files for targeting
    skills_dir = os.path.join(boros_dir, "skills")
    skill_targets = []
    if os.path.isdir(skills_dir):
        for skill_name in os.listdir(skills_dir):
            func_dir = os.path.join(skills_dir, skill_name, "functions")
            if os.path.isdir(func_dir):
                for py_file in glob.glob(os.path.join(func_dir, "*.py")):
                    if os.path.basename(py_file) != "__init__.py" and not py_file.endswith("__"):
                        size = os.path.getsize(py_file)
                        skill_targets.append({
                            "skill": skill_name,
                            "file": os.path.relpath(py_file, kernel.boros_root if kernel else "."),
                            "size_bytes": size,
                            "likely_stub": size < 150,
                            "related_to_weakest": skill_name in related_skills
                        })

    # Filter recently targeted files to force diversity
    recent_targets = []
    records_dir = os.path.join(boros_dir, "memory", "evolution_records")
    if os.path.isdir(records_dir):
        prop_files = sorted(glob.glob(os.path.join(records_dir, "prop-*.json")), key=os.path.getmtime, reverse=True)
        for rec in prop_files:
            try:
                with open(rec) as f:
                    prop = json.load(f)
                    target = prop.get("target_file", "").replace('\\', '/')
                    if target:
                        recent_targets.append(target)
            except:
                pass
    recent_targets = list(dict.fromkeys(recent_targets))[:5]

    filtered_targets = []
    for target in skill_targets:
        file_path_norm = target["file"].replace('\\', '/')
        if any(rt and file_path_norm.endswith(rt.split('/')[-1]) for rt in recent_targets):
            continue  # Skip recently targeted files

        # Priority score: lower is better
        # related_skills files get massive priority boost (lower score)
        score = target["size_bytes"] / 1000.0
        if target["related_to_weakest"]:
            score *= 0.1  # 10x priority for world-model-related skills
        target["priority_score"] = score
        filtered_targets.append(target)

    if not filtered_targets:
        filtered_targets = skill_targets

    # Sort by priority score (world-model-related first, then by size)
    filtered_targets.sort(key=lambda x: x.get("priority_score", 999))
    
    import random
    # Select from top candidates: prefer related skills
    related = [t for t in filtered_targets if t.get("related_to_weakest")]
    if len(related) >= 3:
        candidates = related[:max(5, len(related))]
    else:
        candidates = filtered_targets[:max(5, len(filtered_targets) // 5)]
    random.shuffle(candidates)

    if weakest_score == float("inf"):
        weakest_score = 999.0

    return {
        "status": "ok",
        "weakest_category": weakest_category,
        "weakest_score": weakest_score,
        "related_skills": related_skills,
        "high_water_marks": high_water,
        "latest_scores": latest_scores,
        "history_entries": len(history),
        "candidates": candidates[:10],
        "total_skill_files": len(skill_targets),
        "recommendation": (
            f"Weakest category: '{weakest_category}' (score: {weakest_score:.2f}). "
            f"Related skills: {related_skills}. "
            f"Found {len(candidates)} candidate files. Target one related to the weakest category."
        )
    }
