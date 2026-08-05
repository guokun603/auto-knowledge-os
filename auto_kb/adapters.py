from __future__ import annotations

import hashlib
import importlib.util
import os
from dataclasses import dataclass
from typing import Any

from .store import KnowledgeStore


@dataclass
class AdapterStatus:
    name: str
    mode: str
    available: bool
    detail: str


def embed_text(text: str, dim: int = 16) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).digest()
    values = []
    for i in range(dim):
        b = digest[i % len(digest)]
        values.append((b / 127.5) - 1.0)
    return values


def point_id(text: str) -> int:
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big") & ((1 << 63) - 1)


def external_integrations_disabled() -> bool:
    return os.environ.get("AUTO_KB_DISABLE_EXTERNAL", "").strip().lower() in {"1", "true", "yes"}


def module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def qdrant_enabled() -> bool:
    return os.environ.get("AUTO_KB_ENABLE_QDRANT", "").strip().lower() in {"1", "true", "yes"}


def probe_adapter_statuses(store: KnowledgeStore) -> list[AdapterStatus]:
    disabled = external_integrations_disabled()
    if disabled:
        detail = "external integrations disabled by AUTO_KB_DISABLE_EXTERNAL"
        return [
            AdapterStatus("mem0", "sqlite-fallback", False, detail),
            AdapterStatus("graphiti", "sqlite-fallback", False, detail),
            AdapterStatus("qdrant", "sqlite-keyword-fallback", False, detail),
            AdapterStatus("langgraph", "local-checkpoint-graph", False, detail),
        ]
    return [
        AdapterStatus("mem0", "external-sdk-local-store" if module_available("mem0") else "sqlite-fallback", module_available("mem0"), f"mem0 package {'found' if module_available('mem0') else 'not found'}; local fallback remains SQLite"),
        AdapterStatus("graphiti", "external-sdk-local-edges" if module_available("graphiti_core") else "sqlite-fallback", module_available("graphiti_core"), f"graphiti_core package {'found' if module_available('graphiti_core') else 'not found'}; local fallback remains SQLite"),
        AdapterStatus("qdrant", "external-local-qdrant" if module_available("qdrant_client") and qdrant_enabled() else "sqlite-keyword-primary", module_available("qdrant_client") and qdrant_enabled(), f"qdrant_client package {'found' if module_available('qdrant_client') else 'not found'}; Qdrant disabled by default because hash embeddings are not semantic; set AUTO_KB_ENABLE_QDRANT=1 only for experiments"),
        AdapterStatus("langgraph", "external-stategraph" if module_available("langgraph") else "local-checkpoint-graph", module_available("langgraph"), f"langgraph package {'found' if module_available('langgraph') else 'not found'}; local checkpoints remain SQLite"),
    ]


class Mem0Adapter:
    def __init__(self, store: KnowledgeStore) -> None:
        self.store = store
        if external_integrations_disabled():
            self.status = AdapterStatus("mem0", "sqlite-fallback", False, "external integrations disabled by AUTO_KB_DISABLE_EXTERNAL")
            return
        try:
            mem0_dir = store.root / "memory" / "mem0_home"
            mem0_dir.mkdir(parents=True, exist_ok=True)
            os.environ.setdefault("MEM0_DIR", str(mem0_dir))
            os.environ.setdefault("MEM0_TELEMETRY", "False")
            import mem0  # type: ignore  # noqa: F401
            self.status = AdapterStatus("mem0", "external-sdk-local-store", True, f"mem0 import available; MEM0_DIR={mem0_dir}; SQLite remains local durable fallback")
        except Exception as exc:
            self.status = AdapterStatus("mem0", "sqlite-fallback", False, str(exc))

    def add(self, key: str, value: str, scope: str = "global") -> None:
        self.store.add_memory(key, value, scope)

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        with self.store.connect() as con:
            rows = con.execute("select * from memories where key like ? or value like ? limit ?", (f"%{query}%", f"%{query}%", limit)).fetchall()
        return [dict(r) for r in rows]


class GraphitiAdapter:
    def __init__(self, store: KnowledgeStore) -> None:
        self.store = store
        if external_integrations_disabled():
            self.status = AdapterStatus("graphiti", "sqlite-fallback", False, "external integrations disabled by AUTO_KB_DISABLE_EXTERNAL")
            return
        try:
            import graphiti_core  # type: ignore  # noqa: F401
            self.status = AdapterStatus("graphiti", "external-sdk-local-edges", True, "graphiti_core import available; SQLite edge log remains local fallback without Neo4j config")
        except Exception as exc:
            self.status = AdapterStatus("graphiti", "sqlite-fallback", False, str(exc))

    def add_edge(self, source: str, relation: str, target: str) -> None:
        self.store.add_graph_edge(source, relation, target)

    def query(self, node: str) -> list[dict[str, Any]]:
        with self.store.connect() as con:
            rows = con.execute("select * from graph_edges where source=? or target=?", (node, node)).fetchall()
        return [dict(r) for r in rows]


class VectorAdapter:
    collection = "auto_kb"
    dim = 16

    def __init__(self, store: KnowledgeStore) -> None:
        self.store = store
        self.client = None
        if external_integrations_disabled():
            self.status = AdapterStatus("qdrant", "sqlite-keyword-fallback", False, "external integrations disabled by AUTO_KB_DISABLE_EXTERNAL")
            return
        if not qdrant_enabled():
            self.status = AdapterStatus("qdrant", "sqlite-keyword-primary", False, "Qdrant disabled by default; current local hash embeddings are not semantic")
            return
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
            qpath = store.root / "vector" / "qdrant_local"
            qpath.mkdir(parents=True, exist_ok=True)
            self.client = QdrantClient(path=str(qpath))
            if not self.client.collection_exists(self.collection):
                self.client.create_collection(self.collection, vectors_config=VectorParams(size=self.dim, distance=Distance.COSINE))
            self.status = AdapterStatus("qdrant", "external-local-qdrant", True, f"qdrant local collection: {qpath}")
        except Exception as exc:
            self.status = AdapterStatus("qdrant", "sqlite-keyword-fallback", False, str(exc))

    def index_markdown(self) -> int:
        count = 0
        if self.client is not None:
            from qdrant_client.models import PointStruct
            points = []
            for path in self.store.iter_markdown("knowledge"):
                rel = str(path.relative_to(self.store.root))
                content = path.read_text(encoding="utf-8", errors="ignore")
                points.append(PointStruct(id=point_id(rel), vector=embed_text(content, self.dim), payload={"path": rel, "preview": content[:300]}))
                self.store.index_document(path)
                count += 1
            if points:
                self.client.upsert(collection_name=self.collection, points=points)
            return count
        for path in self.store.iter_markdown("knowledge"):
            self.store.index_document(path)
            count += 1
        return count

    def search(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        if self.client is not None:
            res = self.client.query_points(collection_name=self.collection, query=embed_text(query, self.dim), limit=limit, with_payload=True)
            return [{"score": float(p.score), "path": p.payload.get("path"), "preview": p.payload.get("preview", "")} for p in res.points]
        return self.store.search(query, limit)


class LangGraphAdapter:
    def __init__(self, store: KnowledgeStore) -> None:
        self.store = store
        self.app = None
        if external_integrations_disabled():
            self.status = AdapterStatus("langgraph", "local-checkpoint-graph", False, "external integrations disabled by AUTO_KB_DISABLE_EXTERNAL")
            return
        try:
            from langgraph.graph import END, START, StateGraph
            graph = StateGraph(dict)
            graph.add_node("checkpoint", lambda state: state)
            graph.add_edge(START, "checkpoint")
            graph.add_edge("checkpoint", END)
            self.app = graph.compile()
            self.status = AdapterStatus("langgraph", "external-stategraph", True, "real LangGraph StateGraph compiled")
        except Exception as exc:
            self.status = AdapterStatus("langgraph", "local-checkpoint-graph", False, str(exc))

    def checkpoint(self, workflow: str, node: str, state: dict[str, Any]) -> None:
        if self.app is not None:
            self.app.invoke({"workflow": workflow, "node": node, "state": state})
        self.store.checkpoint(workflow, node, state)
