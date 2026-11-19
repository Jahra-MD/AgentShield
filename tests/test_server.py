
import json
import secrets
from pathlib import Path

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("AgentShield Portfolio Server")

# Resolve relative to this file, not the terminal's working directory.
BASE_DIR = Path(__file__).resolve().parent.parent
PROFILE_PATH = BASE_DIR / "demo_data" / "developer_profile.json"


def load_profile() -> dict:
    """Load the developer portfolio from a local JSON file."""
    with PROFILE_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@mcp.tool()
def get_developer_profile() -> dict:
    """Retrieve the developer's professional profile."""
    profile = load_profile()

    return {
        "name": profile["name"],
        "role": profile["role"],
        "experience": profile["experience"],
        "summary": profile["summary"],
    }


@mcp.tool()
def get_technical_skills(category: str = "all") -> dict:
    """
    Retrieve the developer's technical skills.

    Categories: frontend, backend, databases, messaging, ai, all.
    """
    skills = load_profile()["skills"]

    if category == "all":
        return skills

    if category not in skills:
        return {
            "error": "Unknown category",
            "available_categories": list(skills.keys()),
        }

    return {category: skills[category]}


@mcp.tool()
def get_project_details(project_name: str) -> dict:
    """
    Retrieve details about a developer project.

    Available projects:
    enterprise_hrms, ai_hr_assistant, agentshield.
    """
    projects = load_profile()["projects"]
    project_key = project_name.strip().lower()

    if project_key not in projects:
        return {
            "error": "Project not found",
            "available_projects": list(projects.keys()),
        }

    return projects[project_key]


@mcp.tool()
def get_career_achievements() -> list[str]:
    """Retrieve the developer's engineering achievements."""
    return load_profile()["achievements"]


@mcp.tool()
def generate_verification_code() -> str:
    """
    Generate a new random portfolio verification code.

    The code is created at execution time and cannot
    be predicted before this tool runs.
    """
    return secrets.token_hex(8)


if __name__ == "__main__":
    mcp.run(transport="stdio")
