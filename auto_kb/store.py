from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from difflib import SequenceMatcher
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
ACTION_STATUSES = {"pending", "resolved", "needs-review", "rejected"}
ACTION_CLOSED_STATUSES = {"resolved", "needs-review", "rejected"}
CANDIDATE_STATUSES = {"candidate", "verified", "accepted", "needs-review", "rejected", "published", "duplicate"}
CANDIDATE_PENDING_STATUSES = {"candidate", "verified"}
ACTION_RE = re.compile(r"^- \[(?P<status>[^\]]+)\] (?P<id>RA-\d+) \((?P<kind>[^)]+)\) (?P<path>.+?) :: (?P<summary>.*)$")
KB_FILE_RE = re.compile(r"^KB-(?P<number>\d+)-")
TEMPLATE_FIELD_RE = re.compile(
    r"^- (?:id|kb_number|type|scope|status|source_task|tags|created_at|published_at)\s*:",
    re.IGNORECASE,
)
TEMPLATE_HEADING_RE = re.compile(r"^#{1,6}\s*(?:evidence|conclusion)\s*$", re.IGNORECASE)
# Cap how many matched pitfalls become hard task obligations. Without a cap the
# number of Required Actions grows with the knowledge base, so a trivial task
# eventually has to close a dozen unrelated items before it can pass the gate.
MAX_RISK_HITS = 3
# Task IDs: TASK-YYYYMMDD-HHMMSS-microseconds-slug. Reject path traversal.
VALID_TASK_ID = re.compile(r"^TASK-\d{8}-\d{6}-\d{1,7}-[\w一-鿿-]+$")
# Match "Gate: PASS" or "Gate: NEEDS-REVIEW" on its own line in preflight.
GATE_LINE_RE = re.compile(r"^Gate: (PASS|NEEDS-REVIEW)$", re.MULTILINE)


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def slugify(text: str, max_len: int = 48) -> str:
    text = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text.strip(), flags=re.UNICODE)
    text = re.sub(r"-+", "-", text).strip("-").lower()
    return (text or "task")[:max_len]


def normalize_knowledge_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", text, flags=re.UNICODE)


def strip_template_noise(text: str) -> str:
    """Drop publish-template scaffolding so search scores real content.

    `publish_candidate` writes the same metadata field list and the same
    `## Evidence` / `## Conclusion` headings into every published file. Left in,
    they make words like `type`, `scope`, and `tags` match the whole knowledge
    base, which drowns real hits and manufactures bogus preflight risk hits.
    """
    kept = []
    for line in text.splitlines():
        stripped = line.strip()
        if TEMPLATE_FIELD_RE.match(stripped) or TEMPLATE_HEADING_RE.match(stripped):
            continue
        kept.append(line)
    return "\n".join(kept)


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
        con = sqlite3.connect(self.db_path, timeout=30, factory=ClosingConnection)
        con.row_factory = sqlite3.Row
        con.execute("pragma busy_timeout=5000")
        con.execute("pragma journal_mode=WAL")
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
        with self.connect() as con:
            self._init_fts(con)

    def _init_fts(self, con: sqlite3.Connection) -> None:
        """Create FTS5 index if available; silently no-op otherwise."""
        try:
            con.execute("create virtual table if not exists knowledge_fts using fts5(path, content, tokenize='unicode61')")
            # Backfill from existing knowledge files if FTS is empty
            row = con.execute("select count(*) as cnt from knowledge_fts").fetchone()
            if row and row["cnt"] == 0:
                docs = con.execute("select path, content from vector_docs").fetchall()
                if docs:
                    for doc in docs:
                        cleaned = strip_template_noise(doc["content"])
                        con.execute("insert into knowledge_fts(path, content) values(?, ?)", (doc["path"], cleaned))
                else:
                    # Fresh checkout: index knowledge markdown files directly from disk
                    for path in self.iter_markdown("knowledge"):
                        rel = str(path.relative_to(self.root))
                        content = path.read_text(encoding="utf-8", errors="ignore")
                        cleaned = strip_template_noise(content)
                        con.execute("insert into knowledge_fts(path, content) values(?, ?)", (rel, cleaned))
        except sqlite3.OperationalError:
            pass  # FTS5 not available in this SQLite build; keyword search remains the fallback

    def _fts_available(self, con: sqlite3.Connection) -> bool:
        try:
            con.execute("select count(*) from knowledge_fts")
            return True
        except sqlite3.OperationalError:
            return False

    def _seed_files(self) -> None:
        marker = self.root / ".auto_kb" / "seeded"
        if marker.exists():
            return
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
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(now(), encoding="utf-8")
    def record_event(self, source: str, payload: dict) -> None:
        with self.connect() as con:
            con.execute("insert into events(source,payload,created_at) values(?,?,?)", (source, json.dumps(payload, ensure_ascii=False), now()))

    def set_current_task(self, task_id: str) -> None:
        self.current_task_path.parent.mkdir(parents=True, exist_ok=True)
        self.current_task_path.write_text(task_id, encoding="utf-8")

    def get_current_task(self) -> str | None:
        return self.current_task_path.read_text(encoding="utf-8").strip() if self.current_task_path.exists() else None

    def resolve_task(self, task: str | None) -> str | None:
        resolved = self.get_current_task() if task in (None, "", "current") else task
        if resolved is None:
            return None
        if not VALID_TASK_ID.match(resolved):
            raise ValueError(f"invalid task id: {resolved}")
        return resolved

    def create_task(self, title: str, goal: str | None = None) -> str:
        self.init()
        task_id = f"TASK-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}-{slugify(title)}"
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

    # Windows reserved device names (case-insensitive)
    _RESERVED_NAMES = {n.lower() for n in ("con", "prn", "aux", "nul", "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9", "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9")}

    def add_evidence(self, task_id: str, name: str, content: str) -> Path:
        evidence_name = Path(name)
        if evidence_name.is_absolute() or evidence_name.name != name or name in {"", ".", ".."}:
            raise ValueError(f"invalid evidence file name: {name}")
        stem = evidence_name.stem.lower()
        if stem in self._RESERVED_NAMES:
            raise ValueError(f"invalid evidence file name (reserved): {name}")
        path = self.root / "tasks" / task_id / "evidence" / evidence_name.name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.append_log(task_id, f"evidence added: evidence/{evidence_name.name}")
        return path

    def stage_candidate(self, summary: str, type: str = "lesson", scope: str = "repository", evidence: str = "", source_task: str | None = None, tags: str = "") -> int:
        self.init()
        source_task = self.resolve_task(source_task)
        if not source_task:
            raise ValueError("candidate knowledge must be attached to a task; create or pass --task explicitly")
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
        statuses = sorted(CANDIDATE_PENDING_STATUSES)
        placeholders = ",".join("?" for _ in statuses)
        sql = f"select * from candidates where status in ({placeholders})"
        args: list[str] = list(statuses)
        if task_id:
            sql += " and source_task=?"
            args.append(task_id)
        with self.connect() as con:
            rows = con.execute(sql, args).fetchall()
        return [Candidate(**dict(r)) for r in rows]
    def set_candidate_status(self, id: int, status: str, note: str = "") -> Candidate:
        if status not in CANDIDATE_STATUSES:
            raise ValueError(f"invalid candidate status: {status}")
        cand = self.get_candidate(id)
        if status == "accepted":
            path = self.publish_candidate(id, status="accepted")
            updated = self.get_candidate(id)
            self.record_event("kb.candidate_status", {"id": id, "from": cand.status, "to": updated.status, "note": note, "published_path": str(path.relative_to(self.root))})
            if updated.source_task:
                self.append_log(updated.source_task, f"candidate {id} accepted and published: {note or 'no note'}")
            return updated
        with self.connect() as con:
            con.execute("update candidates set status=? where id=?", (status, id))
        self.record_event("kb.candidate_status", {"id": id, "from": cand.status, "to": status, "note": note})
        if cand.source_task:
            self.append_log(cand.source_task, f"candidate {id} marked {status}: {note or 'no note'}")
        return self.get_candidate(id)
    def next_kb_number(self) -> int:
        max_number = 0
        for path in self.iter_markdown("knowledge"):
            match = KB_FILE_RE.match(path.name)
            if match:
                max_number = max(max_number, int(match.group("number")))
        return max_number + 1

    def make_kb_path(self, folder: str, summary: str) -> Path:
        number = self.next_kb_number()
        slug = slugify(summary)
        while True:
            path = self.root / "knowledge" / folder / f"KB-{number:04d}-{slug}.md"
            if not path.exists():
                return path
            number += 1

    def publish_candidate(self, id: int, status: str = "published") -> Path:
        cand = self.get_candidate(id)
        folder = ROUTES.get(cand.type, "runbooks")
        existing = self.find_published_duplicate(cand.summary)
        if existing is not None:
            rel = str(existing.relative_to(self.root))
            with self.connect() as con:
                con.execute("update candidates set status=?, published_path=? where id=?", ("duplicate", rel, id))
            self.add_graph_edge(f"candidate:{id}", "duplicate_of", rel)
            self.record_event("kb.publish.duplicate", {"id": id, "path": rel})
            return existing

        path = self.make_kb_path(folder, cand.summary)
        body = f"# {cand.summary}\n\n- id: {id}\n- kb_number: {path.name.split('-', 2)[1]}\n- type: {cand.type}\n- scope: {cand.scope}\n- status: {status}\n- source_task: {cand.source_task}\n- tags: {cand.tags}\n- created_at: {cand.created_at}\n- published_at: {now()}\n\n## Evidence\n\n{cand.evidence or 'No external evidence recorded.'}\n\n## Conclusion\n\n{cand.summary}\n"
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

    def _document_title_and_conclusion(self, path: Path) -> tuple[str, str]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        title = ""
        for line in text.splitlines():
            if line.startswith("# "):
                title = line.lstrip("# ").strip()
                break
        conclusion = ""
        marker = "## Conclusion"
        if marker in text:
            body = text.split(marker, 1)[1].strip()
            conclusion = body.splitlines()[0].strip() if body else ""
        return title, conclusion

    def _is_duplicate_summary(self, left: str, right: str) -> bool:
        left_norm = normalize_knowledge_text(left)
        right_norm = normalize_knowledge_text(right)
        if not left_norm or not right_norm:
            return False
        if left_norm == right_norm:
            return True
        if min(len(left_norm), len(right_norm)) >= 12:
            return SequenceMatcher(None, left_norm, right_norm).ratio() >= 0.96
        return False

    def find_published_duplicate(self, summary: str, folder: str | None = None) -> Path | None:
        search_root = self.root / "knowledge" / folder if folder else self.root / "knowledge"
        paths = search_root.rglob("*.md") if search_root.exists() else []
        for path in paths:
            title, conclusion = self._document_title_and_conclusion(path)
            if self._is_duplicate_summary(summary, title) or self._is_duplicate_summary(summary, conclusion):
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
        content = (self.root / rel).read_text(encoding="utf-8", errors="ignore")
        with self.connect() as con:
            con.execute("delete from vector_docs where path=?", (rel,))
            con.execute("insert into vector_docs(path,content,tags,created_at) values(?,?,?,?)", (rel, content, "", now()))
            if self._fts_available(con):
                con.execute("delete from knowledge_fts where path=?", (rel,))
                con.execute("insert into knowledge_fts(path, content) values(?, ?)", (rel, strip_template_noise(content)))

    def search(self, query: str, limit: int = 8) -> list[dict]:
        # Prefer FTS5 full-text search when available (BM25 ranking, O(log n)).
        with self.connect() as con:
            if self._fts_available(con):
                try:
                    fts_query = self._build_fts_query(query)
                    rows = con.execute(
                        "select path, content, rank from knowledge_fts where knowledge_fts match ? order by rank limit ?",
                        (fts_query, limit),
                    ).fetchall()
                    if rows:
                        return [
                            {"score": round(1.0 / max(float(r["rank"]), 0.001), 4), "path": r["path"], "preview": r["content"][:300]}
                            for r in rows
                        ]
                except sqlite3.OperationalError:
                    pass  # Fall through to keyword search on FTS syntax error

        # Keyword fallback for when FTS5 is unavailable or throws on special characters.
        raw_terms = [t.lower() for t in re.findall(r"[\w\u4e00-\u9fff]+", query)]
        weighted_terms: list[tuple[str, int]] = []
        for term in raw_terms:
            weighted_terms.append((term, 3))
            if re.search(r"[\u4e00-\u9fff]", term):
                for size in (3, 4):
                    if len(term) > size:
                        weighted_terms.extend((term[i:i + size], 1) for i in range(0, len(term) - size + 1))
        deduped: dict[str, int] = {}
        for term, weight in weighted_terms:
            if term:
                deduped[term] = max(deduped.get(term, 0), weight)
        hits = []
        for path in self.iter_markdown("knowledge"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            lower = strip_template_noise(text).lower()
            raw_score = sum(weight for term, weight in deduped.items() if term in lower)
            if raw_score:
                score = round(raw_score * 1000 / max(len(lower), 200), 4)
                hits.append((score, path, text[:300]))
        hits.sort(key=lambda x: x[0], reverse=True)
        return [{"score": s, "path": str(p.relative_to(self.root)), "preview": prev} for s, p, prev in hits[:limit]]

    def _build_fts_query(self, query: str) -> str:
        """Build a safe FTS5 query string from user input."""
        terms = [t for t in re.findall(r"[\w\u4e00-\u9fff]+", query) if len(t) >= 2]
        if not terms:
            terms = [query.strip().replace("'", "''")]
        # Join with OR so any matching term contributes to rank.
        return " OR ".join(f'"{t}"' for t in terms[:8])
    def _knowledge_title(self, rel_path: str) -> str:
        path = self.root / rel_path
        if not path.exists():
            return rel_path
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("# "):
                return line.lstrip("# ").strip()
        return rel_path

    def _build_required_actions(self, risk_hits: list[dict]) -> list[dict]:
        actions = []
        for idx, hit in enumerate(risk_hits, start=1):
            actions.append({
                "id": f"RA-{idx:03d}",
                "kind": "pitfall",
                "path": hit["path"],
                "summary": f"Review and handle: {self._knowledge_title(hit['path'])}",
                "status": "pending",
            })
        if risk_hits:
            actions.append({
                "id": f"RA-{len(actions) + 1:03d}",
                "kind": "discussion",
                "path": "knowledge/discussions",
                "summary": "If the task has uncertain or non-final conclusions, stage them as discussion/needs-review instead of publishing as fact.",
                "status": "pending",
            })
        return actions

    def parse_required_actions(self, task_id: str | None = None) -> list[dict]:
        task_id = self.resolve_task(task_id)
        if not task_id:
            return []
        preflight_path = self.root / "tasks" / task_id / "preflight.md"
        if not preflight_path.exists():
            return []
        actions = []
        for line in preflight_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            match = ACTION_RE.match(line.strip())
            if match:
                item = match.groupdict()
                actions.append(item)
        return actions

    def resolve_required_action(self, task_id: str | None, action_id: str, status: str = "resolved", note: str = "") -> list[dict]:
        task_id = self.resolve_task(task_id)
        if not task_id:
            raise ValueError("no task")
        if status not in ACTION_STATUSES:
            raise ValueError(f"invalid action status: {status}")
        preflight_path = self.root / "tasks" / task_id / "preflight.md"
        if not preflight_path.exists():
            raise FileNotFoundError(f"missing preflight.md for task {task_id}")
        lines = preflight_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        changed = []
        updated_lines = []
        for line in lines:
            match = ACTION_RE.match(line.strip())
            if match and (action_id == "all" or match.group("id") == action_id):
                base_summary = match.group("summary").split(" -- ", 1)[0].strip()
                safe_note = note.replace("\n", " ").replace("\r", "") if note else ""
                suffix = f" -- {safe_note}" if safe_note else ""
                line = f"- [{status}] {match.group('id')} ({match.group('kind')}) {match.group('path')} :: {base_summary}{suffix}"
                changed.append(match.group("id"))
            updated_lines.append(line)
        if not changed and action_id == "all":
            self.append_log(task_id, f"required action all marked {status}: no matching actions")
            return self.parse_required_actions(task_id)
        if not changed:
            raise KeyError(f"required action not found: {action_id}")
        preflight_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
        self.append_log(task_id, f"required action {action_id} marked {status}: {note or 'no note'}")
        self.record_event("task.required_action", {"task_id": task_id, "action_id": action_id, "status": status, "note": note, "changed": changed})
        return self.parse_required_actions(task_id)
    def preflight(self, task_id: str | None, goal: str, dry_run: bool = False) -> dict:
        task_id = self.resolve_task(task_id)
        created = False
        if not task_id:
            if dry_run:
                task_id = f"DRY-RUN-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            else:
                task_id = self.create_task(goal, goal)
                created = True
        hits = self.search(goal, limit=10)
        matched_risks = [h for h in hits if "pitfalls" in h["path"]]
        # Only the highest-scoring pitfalls become blocking obligations. The rest
        # stay listed as context so nothing is hidden, just not gate-blocking.
        risk_hits = matched_risks[:MAX_RISK_HITS]
        deferred_risks = matched_risks[MAX_RISK_HITS:]
        required_actions = self._build_required_actions(risk_hits)
        discussion_required = bool(risk_hits) or len(goal.strip()) < 6
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
        lines = ["# Preflight", "", "Preflight-Version: 2", f"Task: {task_id}", f"Goal: {goal}", f"Gate: {gate}", "", "## Warnings"]
        lines += [f"- {w}" for w in warnings] or ["- None"]
        lines += ["", "## Discussion Routing", f"- discussion_required: {'yes' if discussion_required else 'no'}", "- discussion_paths:"]
        lines += ["  - knowledge/discussions"] if discussion_required else ["  - None"]
        lines += ["", "## Required Actions"]
        if required_actions:
            lines += [f"- [{a['status']}] {a['id']} ({a['kind']}) {a['path']} :: {a['summary']}" for a in required_actions]
        else:
            lines += ["- None"]
        lines += ["", "## Related Knowledge"]
        lines += [f"- {h['path']} (score={h['score']})" for h in hits] or ["- None"]
        lines += ["", "## Risk Hits"]
        lines += [f"- {h['path']}" for h in risk_hits] or ["- None"]
        lines += ["", f"## Deferred Risk Hits (context only, not gate-blocking; cap={MAX_RISK_HITS})"]
        lines += [f"- {h['path']} (score={h['score']})" for h in deferred_risks] or ["- None"]
        if not dry_run:
            (self.root / "tasks" / task_id / "preflight.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
            self.append_log(task_id, f"preflight generated: Gate={gate}, related={len(hits)}, risks={len(risk_hits)}, deferred={len(deferred_risks)}")
            self.record_event("task.preflight", {"task_id": task_id, "gate": gate, "hits": hits, "warnings": warnings, "required_actions": required_actions, "deferred_risks": deferred_risks})
        result = {"task_id": task_id, "gate": gate, "hits": hits, "risk_hits": risk_hits, "deferred_risks": deferred_risks, "warnings": warnings, "required_actions": required_actions, "discussion_required": discussion_required}
        if dry_run:
            result["dry_run"] = True
        return result

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
        if not GATE_LINE_RE.search(preflight):
            errors.append("preflight gate is not PASS or NEEDS-REVIEW")
        unresolved_actions = [a for a in self.parse_required_actions(task_id) if a["status"] not in ACTION_CLOSED_STATUSES]
        if unresolved_actions:
            errors.append(f"unresolved preflight required actions: {[a['id'] for a in unresolved_actions]}")
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
        statuses = sorted(CANDIDATE_PENDING_STATUSES)
        placeholders = ",".join("?" for _ in statuses)
        with self.connect() as con:
            rows = con.execute(f"select * from candidates where status in ({placeholders}) and coalesce(source_task,'')=''", statuses).fetchall()
        global_pending = [Candidate(**dict(r)) for r in rows]
        if global_pending:
            errors.append(f"global pending candidates without source_task: {[c.id for c in global_pending]}")
        result = {"pass": not errors, "errors": errors, "task_id": task_id}
        self.record_event("gate.check", result)
        return result


