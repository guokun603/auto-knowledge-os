from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import CallToolRequestParams, CallToolResult, ListToolsResult, TextContent, Tool
    MCP_SDK_AVAILABLE = True
    MCP_IMPORT_ERROR: Exception | None = None
except Exception as exc:
    Server = None  # type: ignore[assignment]
    stdio_server = None  # type: ignore[assignment]
    CallToolRequestParams = Any  # type: ignore[misc,assignment]
    CallToolResult = Any  # type: ignore[misc,assignment]
    ListToolsResult = Any  # type: ignore[misc,assignment]
    TextContent = None  # type: ignore[assignment]
    Tool = None  # type: ignore[assignment]
    MCP_SDK_AVAILABLE = False
    MCP_IMPORT_ERROR = exc

from .store import KnowledgeStore
from .workflow import KnowledgeClosureWorkflow

TOOL_DEFINITIONS = {
    "kb.search": {
        "description": "Search authoritative and indexed knowledge.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 8},
            },
            "required": ["query"],
        },
    },
    "kb.stage": {
        "description": "Stage a candidate knowledge item.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "type": {"type": "string", "default": "lesson"},
                "scope": {"type": "string", "default": "repository"},
                "evidence": {"type": "string", "default": ""},
                "task": {"type": "string", "default": "current"},
                "tags": {"type": "string", "default": ""},
            },
            "required": ["summary"],
        },
    },
    "kb.publish": {
        "description": "Publish a candidate to Markdown truth source.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "integer"}},
            "required": ["id"],
        },
    },
    "task.create": {
        "description": "Create task quartet.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "goal": {"type": "string", "default": ""},
            },
            "required": ["title"],
        },
    },
    "task.preflight": {
        "description": "Generate preflight from knowledge.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "default": "current"},
                "goal": {"type": "string"},
            },
            "required": ["goal"],
        },
    },
    "task.gate": {
        "description": "Run closure gate.",
        "inputSchema": {
            "type": "object",
            "properties": {"task": {"type": "string", "default": "current"}},
        },
    },
    "task.resolve_action": {
        "description": "Mark a preflight required action as resolved, needs-review, rejected, or pending.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "default": "current"},
                "id": {"type": "string"},
                "status": {"type": "string", "default": "resolved"},
                "note": {"type": "string", "default": ""},
            },
            "required": ["id"],
        },
    },
    "workflow.run": {
        "description": "Run the full knowledge closure workflow.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "goal": {"type": "string"},
                "conclusion": {"type": "string", "default": ""},
            },
            "required": ["title", "goal"],
        },
    },
}

TOOLS = {name: spec["description"] for name, spec in TOOL_DEFINITIONS.items()}


def call_tool(store: KnowledgeStore, name: str, args: dict[str, Any]) -> Any:
    if name == "kb.search": return store.search(args.get("query", ""), int(args.get("limit", 8)))
    if name == "kb.stage": return {"id": store.stage_candidate(args["summary"], args.get("type", "lesson"), args.get("scope", "repository"), args.get("evidence", ""), args.get("task", "current"), args.get("tags", ""))}
    if name == "kb.publish": return {"path": str(store.publish_candidate(int(args["id"])).relative_to(store.root))}
    if name == "task.create": return {"task_id": store.create_task(args["title"], args.get("goal"))}
    if name == "task.preflight": return store.preflight(args.get("task", "current"), args["goal"])
    if name == "task.gate": return store.gate(args.get("task", "current"))
    if name == "task.resolve_action": return {"required_actions": store.resolve_required_action(args.get("task", "current"), args["id"], args.get("status", "resolved"), args.get("note", ""))}
    if name == "workflow.run":
        result = KnowledgeClosureWorkflow(str(store.root)).run(args["title"], args["goal"], args.get("conclusion"))
        return result.__dict__
    raise ValueError(f"unknown tool: {name}")


def handle(req: dict[str, Any], store: KnowledgeStore) -> dict[str, Any]:
    try:
        if req.get("method") == "tools/list":
            return {"id": req.get("id"), "result": {"tools": [{"name": k, "description": v} for k, v in TOOLS.items()]}}
        if req.get("method") == "tools/call":
            params = req.get("params", {})
            return {"id": req.get("id"), "result": call_tool(store, params["name"], params.get("arguments", {}))}
        return {"id": req.get("id"), "error": {"message": f"unknown method {req.get('method')}"}}
    except Exception as exc:
        return {"id": req.get("id"), "error": {"message": str(exc)}}


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def create_standard_server(root: str | None = None) -> Server:
    if not MCP_SDK_AVAILABLE:
        raise RuntimeError(f"mcp SDK is not installed; JSON-RPC fallback remains available: {MCP_IMPORT_ERROR}")

    root = root or os.environ.get("AUTO_KB_ROOT") or "."
    if os.path.exists(root):
        os.chdir(root)
    store = KnowledgeStore(root)
    store.init()

    async def list_tools(_ctx: Any, _params: Any) -> ListToolsResult:
        return ListToolsResult(
            tools=[
                Tool(
                    name=name,
                    description=spec["description"],
                    inputSchema=spec["inputSchema"],
                )
                for name, spec in TOOL_DEFINITIONS.items()
            ]
        )

    async def call_standard_tool(_ctx: Any, params: CallToolRequestParams) -> CallToolResult:
        result = call_tool(store, params.name, params.arguments or {})
        return CallToolResult(
            content=[TextContent(text=_json_text(result))],
            structuredContent=result if isinstance(result, dict) else {"result": result},
        )

    return Server(
        "central-auto-kb",
        version="1.0.0",
        instructions="Use this server to search and update the central knowledge base at G:\\AI 架构.",
        on_list_tools=list_tools,
        on_call_tool=call_standard_tool,
    )


async def run_standard_server(root: str | None = None) -> None:
    server = create_standard_server(root)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
            raise_exceptions=False,
        )


def main() -> int:
    root = os.environ.get("AUTO_KB_ROOT") or "."
    if os.path.exists(root):
        os.chdir(root)
    store = KnowledgeStore(root)
    store.init()
    for line in sys.stdin:
        if line.strip():
            print(json.dumps(handle(json.loads(line), store), ensure_ascii=False), flush=True)
    return 0


def stdio_main() -> int:
    asyncio.run(run_standard_server())
    return 0


if __name__ == "__main__":
    raise SystemExit(stdio_main())

