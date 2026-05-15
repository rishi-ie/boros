"""
Model Context Protocol (MCP) — tool/resource/prompt definitions.
Standard interface for all Boros tools and resources.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    handler: Callable[..., Any]

    def to_mcp_format(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "outputSchema": self.output_schema,
        }


@dataclass
class Resource:
    uri: str
    name: str
    description: str
    mime_type: str = "text/plain"

    def to_mcp_format(self) -> dict:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


@dataclass
class Prompt:
    name: str
    description: str
    arguments: list[dict] = field(default_factory=list)
    template: str = ""

    def to_mcp_format(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "arguments": self.arguments,
        }


class MCPServer:
    """
    MCP server that exposes all Boros tools, resources, and prompts.
    This is the interface layer between Boros and external systems.
    """

    def __init__(self):
        self.tools: dict[str, Tool] = {}
        self.resources: dict[str, Resource] = {}
        self.prompts: dict[str, Prompt] = {}

    def register_tool(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def register_resource(self, resource: Resource) -> None:
        self.resources[resource.uri] = resource

    def register_prompt(self, prompt: Prompt) -> None:
        self.prompts[prompt.name] = prompt

    def list_tools(self) -> list[dict]:
        return [t.to_mcp_format() for t in self.tools.values()]

    def list_resources(self) -> list[dict]:
        return [r.to_mcp_format() for r in self.resources.values()]

    def list_prompts(self) -> list[dict]:
        return [p.to_mcp_format() for p in self.prompts.values()]

    def call_tool(self, name: str, arguments: dict) -> Any:
        tool = self.tools.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")
        return tool.handler(**arguments)

    def read_resource(self, uri: str) -> Any:
        resource = self.resources.get(uri)
        if not resource:
            raise ValueError(f"Unknown resource: {uri}")
        return resource

    def render_prompt(self, name: str, arguments: dict) -> str:
        prompt = self.prompts.get(name)
        if not prompt:
            raise ValueError(f"Unknown prompt: {name}")
        template = prompt.template
        for key, value in arguments.items():
            template = template.replace(f"{{{key}}}", str(value))
        return template


# Global MCP server instance
_mcp_server: MCPServer | None = None


def get_mcp_server() -> MCPServer:
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServer()
        _setup_boros_tools(_mcp_server)
    return _mcp_server


def _setup_boros_tools(mcp: MCPServer) -> None:
    """Register all built-in Boros tools with MCP."""

    # Tool: Read file
    mcp.register_tool(Tool(
        name="boros_read_file",
        description="Read a file from the Boros filesystem",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
        output_schema={"type": "object", "properties": {"content": {"type": "string"}}},
        handler=lambda path: {"content": open(path, encoding="utf-8").read()},
    ))

    # Tool: Write file
    mcp.register_tool(Tool(
        name="boros_write_file",
        description="Write content to a file",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
        output_schema={"type": "object", "properties": {"success": {"type": "boolean"}}},
        handler=lambda path, content: {"success": bool(open(path, "w", encoding="utf-8").write(content))},
    ))

    # Tool: List skills
    mcp.register_tool(Tool(
        name="boros_list_skills",
        description="List all registered skills",
        input_schema={"type": "object", "properties": {}},
        output_schema={"type": "object", "properties": {"skills": {"type": "array"}}},
        handler=lambda: {"skills": []},  # Populated at runtime
    ))

    # Tool: Get scores
    mcp.register_tool(Tool(
        name="boros_get_scores",
        description="Get current capability scores",
        input_schema={"type": "object", "properties": {}},
        output_schema={"type": "object", "properties": {"scores": {"type": "object"}}},
        handler=lambda: {"scores": {}},
    ))

    # Tool: Execute workflow
    mcp.register_tool(Tool(
        name="boros_execute_workflow",
        description="Execute a skill composition workflow",
        input_schema={
            "type": "object",
            "properties": {
                "workflow": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "steps": {"type": "array"},
                    },
                }
            },
            "required": ["workflow"],
        },
        output_schema={"type": "object"},
        handler=lambda workflow: {"result": "executed", "workflow": workflow.get("name")},
    ))

    # Tool: Get version history
    mcp.register_tool(Tool(
        name="boros_version_log",
        description="Get version control history",
        input_schema={
            "type": "object",
            "properties": {"limit": {"type": "integer", "default": 20}},
        },
        output_schema={"type": "object"},
        handler=lambda limit=20: {"snapshots": []},
    ))

    # Resource: World model
    mcp.register_resource(Resource(
        uri="boros://world-model",
        name="World Model",
        description="The capability graph defining Boros's capabilities and goals",
        mime_type="application/json",
    ))

    # Resource: Session state
    mcp.register_resource(Resource(
        uri="boros://session-state",
        name="Session State",
        description="Current session state (cycle, mode, scores)",
        mime_type="application/json",
    ))

    # Resource: Skill manifest
    mcp.register_resource(Resource(
        uri="boros://skill-manifest",
        name="Skill Manifest",
        description="Registry of all available skills",
        mime_type="application/json",
    ))

    # Prompt: Evolution cycle
    mcp.register_prompt(Prompt(
        name="evolution_cycle",
        description="Run one evolution cycle",
        arguments=[
            {"name": "focus_capability", "description": "Capability to focus on", "required": "true"},
        ],
        template="Analyze {focus_capability} scores, propose improvements, implement, evaluate.",
    ))

    # Prompt: Work cycle
    mcp.register_prompt(Prompt(
        name="work_cycle",
        description="Run one work cycle (digital employee mode)",
        arguments=[
            {"name": "task", "description": "Task description", "required": "true"},
        ],
        template="Complete: {task}",
    ))

    # Prompt: Status report
    mcp.register_prompt(Prompt(
        name="status_report",
        description="Generate a status report",
        arguments=[],
        template="Current state: {mode}, cycle {cycle}, scores {scores}",
    ))