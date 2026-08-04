from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from .adapters import GraphitiAdapter, LangGraphAdapter, Mem0Adapter, VectorAdapter, module_available, probe_adapter_statuses
from .store import KnowledgeStore
from .workflow import KnowledgeClosureWorkflow


def emit(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="auto-kb")
    p.add_argument("--root", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    n = sub.add_parser("new-task"); n.add_argument("title"); n.add_argument("--goal", default=None)
    pf = sub.add_parser("preflight"); pf.add_argument("--task", default="current"); pf.add_argument("--goal", required=True)
    st = sub.add_parser("stage"); st.add_argument("--summary", required=True); st.add_argument("--type", default="lesson"); st.add_argument("--scope", default="repository"); st.add_argument("--evidence", default=""); st.add_argument("--task", default="current"); st.add_argument("--tags", default="")
    pub = sub.add_parser("publish"); pub.add_argument("--id", type=int, required=True)
    se = sub.add_parser("search"); se.add_argument("query"); se.add_argument("--limit", type=int, default=8)
    gt = sub.add_parser("gate"); gt.add_argument("--task", default="current")
    ev = sub.add_parser("evidence"); ev.add_argument("--task", default="current"); ev.add_argument("--name", required=True); ev.add_argument("--content", required=True)
    ra = sub.add_parser("resolve-action"); ra.add_argument("--task", default="current"); ra.add_argument("--id", required=True); ra.add_argument("--status", default="resolved", choices=["pending", "resolved", "needs-review", "rejected"]); ra.add_argument("--note", default="")
    wf = sub.add_parser("workflow"); wf.add_argument("--title", required=True); wf.add_argument("--goal", required=True); wf.add_argument("--conclusion", default=None)
    status_parser = sub.add_parser("status"); status_parser.add_argument("--deep", action="store_true")
    args = p.parse_args(argv)
    root = Path(args.root or os.environ.get("AUTO_KB_ROOT") or ".").resolve()
    if root.exists():
        os.chdir(root)
    store = KnowledgeStore(root)
    if args.cmd == "init":
        store.init(); emit({"ok": True, "root": str(store.root), "db": str(store.db_path)}); return 0
    if args.cmd == "new-task":
        emit({"task_id": store.create_task(args.title, args.goal)}); return 0
    if args.cmd == "preflight":
        emit(store.preflight(args.task, args.goal)); return 0
    if args.cmd == "stage":
        emit({"id": store.stage_candidate(args.summary, args.type, args.scope, args.evidence, args.task, args.tags)}); return 0
    if args.cmd == "publish":
        path = store.publish_candidate(args.id); emit({"published": str(path.relative_to(store.root))}); return 0
    if args.cmd == "search":
        emit({"results": store.search(args.query, args.limit)}); return 0
    if args.cmd == "gate":
        result = store.gate(args.task); emit(result); return 0 if result["pass"] else 2
    if args.cmd == "evidence":
        task_id = store.resolve_task(args.task)
        if not task_id: raise SystemExit("no task")
        path = store.add_evidence(task_id, args.name, args.content); emit({"evidence": str(path.relative_to(store.root))}); return 0
    if args.cmd == "resolve-action":
        emit({"required_actions": store.resolve_required_action(args.task, args.id, args.status, args.note)}); return 0
    if args.cmd == "workflow":
        result = KnowledgeClosureWorkflow(root).run(args.title, args.goal, args.conclusion); emit(result.__dict__); return 0 if result.gate["pass"] else 2
    if args.cmd == "status":
        store.init()
        statuses = [Mem0Adapter(store).status, GraphitiAdapter(store).status, VectorAdapter(store).status, LangGraphAdapter(store).status] if args.deep else probe_adapter_statuses(store)
        mcp_available = module_available("mcp")
        mcp_status = {
            "name": "mcp",
            "mode": "standard-sdk" if mcp_available else "json-rpc-fallback",
            "available": mcp_available,
            "detail": "mcp package found" if mcp_available else "mcp package not found; JSON-RPC fallback remains available",
        }
        emit({"current_task": store.get_current_task(), "status_mode": "deep" if args.deep else "fast", "adapters": [s.__dict__ for s in statuses], "mcp": mcp_status}); return 0
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
