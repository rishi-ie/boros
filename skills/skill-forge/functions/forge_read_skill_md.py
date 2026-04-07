
import os

def forge_read_skill_md(params: dict, kernel=None) -> dict:
    """Read the SKILL.md file for a given skill. Returns full content and parsed sections."""
    boros_dir = str(kernel.boros_root) if kernel else os.getcwd()
    skill_name = params.get("skill_name", "").strip()

    if not skill_name:
        return {"status": "error", "message": "skill_name required"}

    skill_md_path = os.path.join(boros_dir, "skills", skill_name, "SKILL.md")
    if not os.path.exists(skill_md_path):
        return {"status": "error", "message": f"SKILL.md not found for skill '{skill_name}' at {skill_md_path}"}

    try:
        with open(skill_md_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        return {"status": "error", "message": f"Could not read SKILL.md: {e}"}

    # Parse into sections by markdown headers
    sections = {}
    current_section = "header"
    current_lines = []
    for line in content.split("\n"):
        if line.startswith("## "):
            if current_lines:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = line[3:].strip()
            current_lines = []
        elif line.startswith("# "):
            if current_lines:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = "title"
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_lines:
        sections[current_section] = "\n".join(current_lines).strip()

    return {
        "status": "ok",
        "skill_name": skill_name,
        "path": skill_md_path,
        "content": content,
        "sections": sections,
        "section_names": list(sections.keys())
    }
