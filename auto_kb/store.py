from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROUTES = {
    "decision": "decisions",
    "lesson": "pitfalls",
    "pitfall": "pitfalls",
    "runbook": "runbooks",
    "preference": "preferences",
    "discussion": "discussions",
    "boundary": "boundaries",
    "fact": "runbooks",
}
REQUIRED_TASK_FILES = ["goal.md", "plan.md", "preflight.md", "log.md"]


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def slugify(text: str, max_len: int = 48) -> str:
    text = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text.strip(), flags=re.UNICODE)
    text = re.sub(r"-+", "-", text).strip("-").lower()
    return (text or "task")[:max_len]


@dataclass
class Candidate:
    id: int
    type: str
    scope: str
    status: str
    summary: str
    evidence: str
    source_task: str
    tags: str
    created_at: str
    published_path: str | None = None


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


class KnowledgeStore:
    def __init__(self, root: str | Path = ".") -> None:
        self.root = Path(root).resolve()
        self.db_path = self.root / "memory" / "knowledge.db"
        self.current_task_path = self.root / ".auto_kb" / "current_task"

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.db_path, factory=ClosingConnection)
        con.row_factory = sqlite3.Row
        return con

    def init(self) -> None:
        for rel in [
            "knowledge/boundaries", "knowledge/decisions", "knowledge/pitfalls", "knowledge/runbooks",
            "knowledge/preferences", "knowledge/discussions", "tasks", "memory", ".auto_kb",
            "vector", "graph", "gates", "hooks", "tools", "workflows", "mcp-server",
        ]:
            (self.root / rel).mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.executescript(
                """
                create table if not exists events(id integer primary key autoincrement, source text not null, payload text not null, created_at text not null);
                create table if not exists candidates(id integer primary key autoincrement, type text not null, scope text not null, status text not null, summary text not null, evidence text not null, source_task text, tags text, created_at text not null, published_path text);
                create table if not exists checkpoints(id integer primary key autoincrement, workflow text not null, node text not null, state_json text not null, created_at text not null);
                create table if not exists memories(id integer primary key autoincrement, key text not null, value text not null, scope text not null, created_at text not null);
                create table if not exists graph_edges(id integer primary key autoincrement, source text not null, relation text not null, target text not null, valid_from text, created_at text not null);
                create table if not exists vector_docs(id integer primary key autoincrement, path text not null, content text not null, tags text, created_at text not null);
                """
            )
            con.execute("delete from vector_docs where id not in (select max(id) from vector_docs group by path)")
            con.execute("create unique index if not exists idx_vector_docs_path on vector_docs(path)")
        self._seed_files()

    def _seed_files(self) -> None:
        seeds = {
            "knowledge/README.md": "# Knowledge Index\n\nAuthoritative Markdown knowledge lives here. Derived indexes must be rebuildable from this folder.\n",
            "knowledge/pitfalls/PIT-001-no-evidence-no-completion.md": "# PIT-001 No Evidence, No Completion\n\n- type: pitfall\n- status: accepted\n- trigger: task claims completion without test, file, command, screenshot, log, or other reviewable evidence.\n- gate: evidence must exist or the task must explicitly prove no evidence is required.\n- mitigation: write evidence under task `evidence/` and cite it in `log.md`.\n",
            "knowledge/pitfalls/PIT-002-no-preflight-no-start.md": "# PIT-002 No Preflight, No Start\n\n- type: pitfall\n- status: accepted\n- trigger: substantial task starts without goal, plan, preflight, and known-risk scan.\n- gate: `preflight.md` must contain `Gate: PASS` or `Gate: NEEDS-REVIEW`.\n- mitigation: run `python -m auto_kb.cli preflight --task current --goal ...`.\n",
            "knowledge/runbooks/RUN-001-knowledge-closure.md": "# RUN-001 Knowledge Closure\n\n1. Create task quartet.\n2. Run preflight.\n3. Execute work and write evidence.\n4. Stage durable knowledge.\n5. Publish accepted or verified knowledge.\n6. Run gate before final response.\n",
        }
        for rel, text in seeds.items():
            path = self.root / rel
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")

    def record_event(self, source: str, payload: dict) -> None:
        with self.connect() as con:
            con.execute("insert into events(source,payload,created_at) values(?,?,?)", (source, json.dumps(payload, ensure_ascii=False), now()))

    def set_current_task(self, task_id: str) -> None:
        self.current_task_path.parent.mkdir(parents=True, exist_ok=True)
        self.current_task_path.write_text(task_id, encoding="utf-8")

    def get_current_task(self) -> str | None:
        return self.current_task_path.read_text(encoding="utf-8").strip() if self.current_task_path.exists() else None

    def resolve_task(self, task: str | None) -> str | None:
        return self.get_current_task() if task in (None, "", "current") else task

    def create_task(self, title: str, goal: str | None = None) -> str:
        self.init()
        task_id = f"TASK-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{slugify(title)}"
        task_dir = self.root / "tasks" / task_id
        (task_dir / "evidence").mkdir(parents=True, exist_ok=True)
        (task_dir / "goal.md").write_text(f"# Goal\n\nTitle: {title}\n\nGoal: {goal or title}\n\nAcceptance:\n- Gate must pass.\n- Evidence must be reviewable.\n", encoding="utf-8")
        (task_dir / "plan.md").write_text("# Plan\n\n- [ ] Run preflight.\n- [ ] Execute task.\n- [ ] Collect evidence.\n- [ ] Publish durable knowledge.\n- [ ] Run gate.\n", encoding="utf-8")
        (task_dir / "preflight.md").write_text("# Preflight\n\nGate: PENDING\n", encoding="utf-8")
        (task_dir / "log.md").write_text(f"# Log\n\n- {now()} task created.\n", encoding="utf-8")
        self.set_current_task(task_id)
        self.record_event("task.create", {"task_id": task_id, "title": title})
        return task_id

    def append_log(self, task_id: str, line: str) -> None:
        with (self.root / "tasks" / task_id / "log.md").open("a", encoding="utf-8") as f:
            f.write(f"- {now()} {line}\n")

    def add_evidence(self, task_id: str, name: str, content: str) -> Path:
        path = self.root / "tasks" / task_id / "evidence" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.append_log(task_id, f"evidence added: evidence/{name}")
        return path

    def stage_candidate(self, summary: str, type: str = "lesson", scope: str = "repository", evidence: str = "", source_task: str | None = None, tags: str = "") -> int:
        self.init()
        source_task = self.resolve_task(source_task) or ""
        with self.connect() as con:
            cur = con.execute("insert into candidates(type,scope,status,summary,evidence,source_task,tags,created_at) values(?,?,?,?,?,?,?,?)", (type, scope, "candidate", summary, evidence, source_task, tags, now()))
            cid = int(cur.lastrowid)
        self.record_event("kb.stage", {"id": cid, "summary": summary, "type": type, "source_task": source_task})
        return cid

    def get_candidate(self, id: int) -> Candidate:
        with self.connect() as con:
            row = con.execute("select * from candidates where id=?", (id,)).fetchone()
        if row is None:
            raise KeyError(f"candidate not found: {id}")
        return Candidate(**dict(row))

    def pending_candidates(self, task_id: str | None = None) -> list[Candidate]:
        task_id = self.resolve_task(task_id)
        sql = "select * from candidates where status in ('candidate','verified','accepted')"
        args = []
        if task_id:
            sql += " and source_task=?"
            args.append(task_id)
        with self.connect() as con:
            rows = con.execute(sql, args).fetchall()
        return [Candidate(**dict(r)) for r in rows]

    def publish_candidate(self, id: int, status: str = "published") -> Path:
        cand = self.get_candidate(id)
        folder = ROUTES.get(cand.type, "runbooks")
        existing = self.find_published_duplicate(cand.summary, folder)
        if existing is not None:
            rel = str(existing.relative_to(self.root))
            with self.connect() as con:
                con.execute("update candidates set status=?, published_path=? where id=?", ("duplicate", rel, id))
            self.add_graph_edge(f"candidate:{id}", "duplicate_of", rel)
            self.record_event("kb.publish.duplicate", {"id": id, "path": rel})
            return existing

        path = self.root / "knowledge" / folder / f"KB-{id:04d}-{slugify(cand.summary)}.md"
        body = f"# {cand.summary}\n\n- id: {id}\n- type: {cand.type}\n- scope: {cand.scope}\n- status: {status}\n- source_task: {cand.source_task}\n- tags: {cand.tags}\n- created_at: {cand.created_at}\n- published_at: {now()}\n\n## Evidence\n\n{cand.evidence or 'No external evidence recorded.'}\n\n## Conclusion\n\n{cand.summary}\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        with self.connect() as con:
            con.execute("update candidates set status=?, published_path=? where id=?", (status, str(path.relative_to(self.root)), id))
        self.index_document(path)
        self.add_graph_edge(f"candidate:{id}", "published_as", str(path.relative_to(self.root)))
        if cand.type == "preference":
            self.add_memory(cand.summary, cand.evidence or cand.summary, scope=cand.scope)
        self.record_event("kb.publish", {"id": id, "path": str(path.relative_to(self.root))})
        return path

    def find_published_duplicate(self, summary: str, folder: str) -> Path | None:
        normalized = " ".join(summary.split()).casefold()
        for path in (self.root / "knowledge" / folder).glob("*.md"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            title = text.splitlines()[0].lstrip("# ").strip() if text.splitlines() else ""
            if " ".join(title.split()).casefold() == normalized:
                return path
            marker = "## Conclusion"
            if marker in text:
                conclusion = text.split(marker, 1)[1].strip().splitlines()[0].strip() if text.split(marker, 1)[1].strip() else ""
                if " ".join(conclusion.split()).casefold() == normalized:
                    return path
        return None

    def add_memory(self, key: str, value: str, scope: str = "global") -> None:
        with self.connect() as con:
            con.execute("insert into memories(key,value,scope,created_at) values(?,?,?,?)", (key, value, scope, now()))

    def add_graph_edge(self, source: str, relation: str, target: str, valid_from: str | None = None) -> None:
        with self.connect() as con:
            con.execute("insert into graph_edges(source,relation,target,valid_from,created_at) values(?,?,?,?,?)", (source, relation, target, valid_from or now(), now()))

    def checkpoint(self, workflow: str, node: str, state: dict) -> None:
        with self.connect() as con:
            con.execute("insert into checkpoints(workflow,node,state_json,created_at) values(?,?,?,?)", (workflow, node, json.dumps(state, ensure_ascii=False), now()))

    def iter_markdown(self, folder: str = "knowledge"):
        base = self.root / folder
        return [] if not base.exists() else base.rglob("*.md")

    def index_document(self, path: Path) -> None:
        rel = str(path.relative_to(self.root)) if path.is_absolute() else str(path)
        content = (self.root / rel).read_text(encoding="utf-8")
        with self.connect() as con:
            con.execute("delete from vector_docs where path=?", (rel,))
            con.execute("insert into vector_docs(path,content,tags,created_at) values(?,?,?,?)", (rel, content, "", now()))

    def search(self, query: str, limit: int = 8) -> list[dict]:
        self.init()
        raw_terms = [t.lower() for t in re.findall(r"[\w\u4e00-\u9fff]+", query)]
        terms: list[str] = []
        for term in raw_terms:
            terms.append(term)
            # Chinese queries are often typed as one phrase without spaces. Add short
            # character windows so searches like "自动化" can hit longer sentences.
            if re.search(r"[\u4e00-\u9fff]", term):
                for size in (2, 3, 4):
                    terms.extend(term[i:i + size] for i in range(0, max(len(term) - size + 1, 0)))
        terms = list(dict.fromkeys(t for t in terms if t))
        hits = []
        for path in self.iter_markdown("knowledge"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            lower = text.lower()
            score = sum(lower.count(t) for t in terms) if terms else 0
            if score:
                hits.append((score, path, text[:300]))
        hits.sort(key=lambda x: x[0], reverse=True)
        return [{"score": s, "path": str(p.relative_to(self.root)), "preview": prev} for s, p, prev in hits[:limit]]

    def preflight(self, task_id: str | None, goal: str) -> dict:
        task_id = self.resolve_task(task_id)
        if not task_id:
            task_id = self.create_task(goal, goal)
        hits = self.search(goal, limit=10)
        risk_hits = [h for h in hits if "pitfalls" in h["path"]]
        warnings = []
        if not goal.strip():
            gate = "FAIL"
            warnings.append("empty goal")
        elif len(goal.strip()) < 6:
            gate = "NEEDS-REVIEW"
            warnings.append("goal is too short to verify intent")
        elif risk_hits:
            gate = "NEEDS-REVIEW"
            warnings.append("related pitfall knowledge requires review")
        else:
            gate = "PASS"
        lines = ["# Preflight", "", f"Task: {task_id}", f"Goal: {goal}", f"Gate: {gate}", "", "## Warnings"]
        lines += [f"- {w}" for w in warnings] or ["- None"]
        lines += ["", "## Related Knowledge"]
        lines += [f"- {h['path']} (score={h['score']})" for h in hits] or ["- None"]
        lines += ["", "## Risk Hits"]
        lines += [f"- {h['path']}" for h in risk_hits] or ["- None"]
        (self.root / "tasks" / task_id / "preflight.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.append_log(task_id, f"preflight generated: Gate={gate}, related={len(hits)}, risks={len(risk_hits)}")
        self.record_event("task.preflight", {"task_id": task_id, "gate": gate, "hits": hits, "warnings": warnings})
        return {"task_id": task_id, "gate": gate, "hits": hits, "risk_hits": risk_hits, "warnings": warnings}

    def gate(self, task_id: str | None = None) -> dict:
        self.init()
        task_id = self.resolve_task(task_id)
        if not task_id:
            return {"pass": False, "errors": ["no current task"], "task_id": None}
        task_dir = self.root / "tasks" / task_id
        errors = []
        for name in REQUIRED_TASK_FILES:
            if not (task_dir / name).exists():
                errors.append(f"missing {name}")
        preflight = (task_dir / "preflight.md").read_text(encoding="utf-8", errors="ignore") if (task_dir / "preflight.md").exists() else ""
        if "Gate: PASS" not in preflight and "Gate: NEEDS-REVIEW" not in preflight:
            errors.append("preflight gate is not PASS or NEEDS-REVIEW")
        evidence_dir = task_dir / "evidence"
        valid_evidence = []
        if evidence_dir.exists():
            for evidence_path in evidence_dir.iterdir():
                if evidence_path.is_file() and evidence_path.stat().st_size > 0:
                    if evidence_path.read_text(encoding="utf-8", errors="ignore").strip():
                        valid_evidence.append(evidence_path)
        if not valid_evidence:
            errors.append("missing non-empty evidence")
        pending = self.pending_candidates(task_id)
        if pending:
            errors.append(f"pending candidates: {[c.id for c in pending]}")
        result = {"pass": not errors, "errors": errors, "task_id": task_id}
        self.record_event("gate.check", result)
        return result







