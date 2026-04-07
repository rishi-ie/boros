
import os, shutil, datetime

def forge_edit_skill_md(params: dict, kernel=None) -> dict:
    """Edit a specific section of a SKILL.md file. Creates a backup before modifying.
    This is the preferred first step in the escalation ladder — semantic before code."""
    boros_dir = str(kernel.boros_root) if kernel else os.getcwd()
    skill_name = params.get("skill_name", "").strip()
    section_name = params.get("section_name", "").strip()
    new_content = params.get("new_content", "")

    if not skill_name:
        return {"status": "error", "message": "skill_name required"}
    if not section_name:
        return {"status": "error", "message": "section_name required (e.g. 'Role', 'Rules', 'Pipeline')"}
    if not new_content:
        return {"status": "error", "message": "new_content required"}

    skill_md_path = os.path.join(boros_dir, "skills", skill_name, "SKILL.md")
    if not os.path.exists(skill_md_path):
        return {"status": "error", "message": f"SKILL.md not found for skill '{skill_name}'"}

    try:
        with open(skill_md_path, "r", encoding="utf-8") as f:
            original = f.read()
    except OSError as e:
        return {"status": "error", "message": f"Could not read SKILL.md: {e}"}

    # Create backup
    backup_dir = os.path.join(boros_dir, "snapshots", "skill_md_backups")
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"{skill_name}_SKILL_{ts}.md.bak")
    try:
        shutil.copy2(skill_md_path, backup_path)
    except OSError as e:
        return {"status": "error", "message": f"Could not create backup: {e}"}

    # Replace or append the section
    target_header = f"## {section_name}"
    lines = original.split("\n")
    new_lines = []
    in_target = False
    section_found = False
    i = 0

    while i < len(lines):
        line = lines[i]
        if line.strip() == target_header:
            # Found the section — replace until next ## header
            in_target = True
            section_found = True
            new_lines.append(line)  # keep the header
            new_lines.append(new_content)
            # Skip old content until next section or end
            i += 1
            while i < len(lines):
                if lines[i].startswith("## "):
                    break
                i += 1
            in_target = False
            continue
        new_lines.append(line)
        i += 1

    if not section_found:
        # Section doesn't exist — append it
        new_lines.append(f"\n{target_header}")
        new_lines.append(new_content)

    updated = "\n".join(new_lines)

    try:
        with open(skill_md_path, "w", encoding="utf-8") as f:
            f.write(updated)
    except OSError as e:
        # Restore backup on write failure
        shutil.copy2(backup_path, skill_md_path)
        return {"status": "error", "message": f"Write failed, backup restored: {e}"}

    action = "updated" if section_found else "appended"
    return {
        "status": "ok",
        "skill_name": skill_name,
        "section": section_name,
        "action": action,
        "backup_path": backup_path,
        "message": f"Section '{section_name}' {action} in {skill_name}/SKILL.md"
    }
