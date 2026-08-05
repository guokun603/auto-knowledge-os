from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .adapters import GraphitiAdapter, LangGraphAdapter, Mem0Adapter, VectorAdapter
from .store import KnowledgeStore


@dataclass
class WorkflowResult:
    task_id: str
    preflight: dict[str, Any]
    gate: dict[str, Any]
    published: list[str]
    adapters: dict[str, dict[str, Any]]


class KnowledgeClosureWorkflow:
    """LangGraph-compatible workflow with a local checkpoint fallback."""

    def __init__(self, root: str = ".") -> None:
        self.store = KnowledgeStore(root)
        self.langgraph = LangGraphAdapter(self.store)
        self.mem0 = Mem0Adapter(self.store)
        self.graphiti = GraphitiAdapter(self.store)
        self.vector = VectorAdapter(self.store)

    def checkpoint(self, node: str, state: dict[str, Any]) -> None:
        self.langgraph.checkpoint("knowledge_closure", node, state)

    def adapter_statuses(self) -> dict[str, dict[str, Any]]:
        return {
            "langgraph": self.langgraph.status.__dict__,
            "mem0": self.mem0.status.__dict__,
            "graphiti": self.graphiti.status.__dict__,
            "vector": self.vector.status.__dict__,
        }

    def run(self, title: str, goal: str, conclusion: str | None = None, dry_run: bool = False) -> WorkflowResult:
        self.store.init()
        if dry_run:
            task_id = f"DRY-RUN-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            preflight = self.store.preflight(None, goal, dry_run=True)
            return WorkflowResult(task_id=task_id, preflight=preflight, gate={"pass": preflight["gate"] in ("PASS", "NEEDS-REVIEW"), "dry_run": True, "task_id": task_id}, published=[], adapters=self.adapter_statuses())
        task_id = self.store.create_task(title, goal)
        self.checkpoint("task_created", {"task_id": task_id, "goal": goal})
        self.mem0.add("last_goal", goal, scope="task")
        self.graphiti.add_edge(f"task:{task_id}", "has_goal", goal)
        preflight = self.store.preflight(task_id, goal)
        self.checkpoint("preflight", preflight)
        evidence_lines = [
            f"Workflow executed for {task_id}",
            f"Goal: {goal}",
            f"Conclusion provided: {'yes' if conclusion and conclusion.strip() else 'no'}",
        ]
        if preflight.get("required_actions"):
            evidence_lines.append("Preflight required actions:")
            for action in preflight["required_actions"]:
                evidence_lines.append(f"- {action['id']} {action['path']} :: {action['summary']}")
        self.store.add_evidence(task_id, "workflow.txt", "\n".join(evidence_lines) + "\n")
        self.checkpoint("evidence", {"task_id": task_id})
        published: list[str] = []
        if conclusion and conclusion.strip():
            cid = self.store.stage_candidate(conclusion, type="lesson", evidence=f"workflow task {task_id}", source_task=task_id)
            self.checkpoint("candidate_staged", {"candidate_id": cid})
            if preflight.get("required_actions"):
                self.checkpoint("candidate_waiting_for_required_actions", {"candidate_id": cid, "required_actions": preflight["required_actions"]})
            else:
                path = self.store.publish_candidate(cid)
                published.append(str(path.relative_to(self.store.root)))
                self.checkpoint("candidate_published", {"candidate_id": cid, "path": published[-1]})
        else:
            cid = self.store.stage_candidate(
                "NEEDS-REVIEW: workflow completed without a verified durable conclusion",
                type="discussion",
                evidence=f"workflow task {task_id} ended without a stable conclusion",
                source_task=task_id,
                tags="needs-review,placeholder",
            )
            self.checkpoint("candidate_staged_needs_review", {"candidate_id": cid})
        self.vector.index_markdown()
        gate = self.store.gate(task_id)
        self.checkpoint("closure_gate", gate)
        return WorkflowResult(task_id=task_id, preflight=preflight, gate=gate, published=published, adapters=self.adapter_statuses())


