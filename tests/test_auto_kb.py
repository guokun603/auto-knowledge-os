from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import os
from pathlib import Path

os.environ.setdefault("AUTO_KB_DISABLE_EXTERNAL", "1")

from auto_kb.store import KnowledgeStore
from auto_kb.workflow import KnowledgeClosureWorkflow
from auto_kb.adapters import VectorAdapter


def run_python(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(kwargs.pop("env_overrides", {}))
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, *args],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=env,
        **kwargs,
    )


class AutoKBTests(unittest.TestCase):
    def test_task_quartet_and_preflight(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            store.init()
            task = store.create_task("证据测试", "需要 evidence 的任务")
            result = store.preflight(task, "需要 evidence 的任务")
            self.assertEqual(result["gate"], "NEEDS-REVIEW")
            self.assertTrue(result["discussion_required"])
            self.assertTrue(result["required_actions"])
            for name in ["goal.md", "plan.md", "preflight.md", "log.md"]:
                self.assertTrue((Path(td) / "tasks" / task / name).exists())
            self.assertTrue(any("pitfalls" in h["path"] for h in result["hits"]))

    def test_gate_blocks_unresolved_preflight_actions(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            store.init()
            task = store.create_task("隐患消费测试", "需要 evidence 的任务")
            store.preflight(task, "需要 evidence 的任务")
            store.add_evidence(task, "proof.txt", "proof")
            result = store.gate(task)
            self.assertFalse(result["pass"])
            self.assertIn("unresolved preflight required actions", " ".join(result["errors"]))

    def test_stage_publish_and_gate(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            store.init()
            task = store.create_task("闭环测试", "测试知识闭环")
            store.preflight(task, "测试知识闭环")
            store.resolve_required_action(task, "all", "resolved", "unit test handled preflight risks")
            store.add_evidence(task, "proof.txt", "proof")
            cid = store.stage_candidate("测试结论必须落库", "lesson", evidence="unit test", source_task=task)
            failed = store.gate(task)
            self.assertFalse(failed["pass"])
            self.assertIn("pending candidates", " ".join(failed["errors"]))
            path = store.publish_candidate(cid)
            self.assertTrue(path.exists())
            passed = store.gate(task)
            self.assertTrue(passed["pass"], passed)

    def test_empty_evidence_does_not_pass_gate(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            store.init()
            task = store.create_task("空证据测试", "测试空证据不能过门禁")
            store.preflight(task, "测试空证据不能过门禁")
            store.resolve_required_action(task, "all", "resolved", "unit test focuses on empty evidence")
            (Path(td) / "tasks" / task / "evidence" / "empty.txt").write_text("", encoding="utf-8")
            result = store.gate(task)
            self.assertFalse(result["pass"])
            self.assertIn("missing non-empty evidence", " ".join(result["errors"]))

    def test_publish_duplicate_reuses_existing_file(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            store.init()
            task = store.create_task("查重测试", "测试重复知识不新建文件")
            first = store.stage_candidate("重复结论", "lesson", evidence="first", source_task=task)
            first_path = store.publish_candidate(first)
            second = store.stage_candidate("重复结论", "lesson", evidence="second", source_task=task)
            second_path = store.publish_candidate(second)
            self.assertEqual(first_path, second_path)
            files = list((Path(td) / "knowledge" / "pitfalls").glob("KB-*-重复结论.md"))
            self.assertEqual(len(files), 1)

    def test_candidate_lifecycle_can_close_without_publish(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            store.init()
            task = store.create_task("候选状态测试", "测试 needs-review 和 rejected 不阻塞 gate")
            store.preflight(task, "测试 needs-review 和 rejected 不阻塞 gate")
            store.resolve_required_action(task, "all", "resolved", "unit test handled preflight risks")
            store.add_evidence(task, "proof.txt", "proof")
            cid = store.stage_candidate("未定结论只需要复查", "discussion", evidence="unit test", source_task=task)
            self.assertFalse(store.gate(task)["pass"])
            store.set_candidate_status(cid, "needs-review", "deferred by unit test")
            self.assertTrue(store.gate(task)["pass"])

    def test_stage_candidate_requires_task_context(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            store.init()
            with self.assertRaises(ValueError):
                store.stage_candidate("没有任务来源的候选知识", "lesson", evidence="unit test")

    def test_gate_blocks_global_pending_candidates(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            store.init()
            task = store.create_task("全局候选测试", "测试空 source_task 候选会被 gate 发现")
            store.preflight(task, "测试空 source_task 候选会被 gate 发现")
            store.resolve_required_action(task, "all", "resolved", "unit test handled preflight risks")
            store.add_evidence(task, "proof.txt", "proof")
            with store.connect() as con:
                con.execute(
                    "insert into candidates(type,scope,status,summary,evidence,source_task,tags,created_at) values(?,?,?,?,?,?,?,?)",
                    ("lesson", "repository", "candidate", "orphan", "unit test", "", "", "2026-08-05T00:00:00"),
                )
            result = store.gate(task)
            self.assertFalse(result["pass"])
            self.assertIn("global pending candidates", " ".join(result["errors"]))

    def test_evidence_name_cannot_escape_task_directory(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            store.init()
            task = store.create_task("路径穿越测试", "测试 evidence 名称不能逃逸任务目录")
            with self.assertRaises(ValueError):
                store.add_evidence(task, "../../../escaped.txt", "bad")
            self.assertFalse((Path(td) / "escaped.txt").exists())

    def test_task_ids_do_not_collide_for_same_title(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            first = store.create_task("同标题", "goal")
            second = store.create_task("同标题", "goal")
            self.assertNotEqual(first, second)
            self.assertTrue((Path(td) / "tasks" / first / "goal.md").exists())
            self.assertTrue((Path(td) / "tasks" / second / "goal.md").exists())

    def test_vector_adapter_defaults_to_keyword_search(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            store.init()
            task = store.create_task("检索测试", "goal")
            cid = store.stage_candidate("关键词检索应该优先于伪语义向量", "lesson", evidence="unit test", source_task=task)
            store.publish_candidate(cid)
            adapter = VectorAdapter(store)
            self.assertIn("keyword", adapter.status.mode)
            results = adapter.search("关键词检索", limit=3)
            self.assertTrue(any("关键词检索应该优先" in hit["preview"] for hit in results))

    def test_cli_candidate_status_closes_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            store.init()
            task = store.create_task("CLI 候选状态测试", "verify candidate-status command")
            store.preflight(task, "verify candidate-status command")
            store.resolve_required_action(task, "all", "resolved", "unit test handled preflight risks")
            store.add_evidence(task, "proof.txt", "proof")
            cid = store.stage_candidate("CLI can defer candidate", "discussion", evidence="unit test", source_task=task)
            proc = run_python(["-m", "auto_kb.cli", "--root", td, "candidate-status", "--id", str(cid), "--status", "needs-review", "--note", "unit test"])
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertTrue(store.gate(task)["pass"])
    def test_workflow_without_conclusion_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            result = KnowledgeClosureWorkflow(td).run("无结论流程", "需要 evidence 的任务")
            self.assertFalse(result.gate["pass"])
            self.assertFalse(result.published)
            self.assertIn("unresolved preflight required actions", " ".join(result.gate["errors"]))
            self.assertIn("pending candidates", " ".join(result.gate["errors"]))

    def test_workflow_runs_full_closure_and_adapters(self):
        with tempfile.TemporaryDirectory() as td:
            result = KnowledgeClosureWorkflow(td).run("工作流测试", "测试自动化闭环和 evidence", "工作流可以自动发布结论")
            self.assertTrue(result.gate["pass"], result.gate)
            self.assertTrue(result.published)
            self.assertIn("langgraph", result.adapters)
            self.assertIn("mem0", result.adapters)
            self.assertIn("graphiti", result.adapters)
            self.assertIn("vector", result.adapters)

    def test_mcp_json_rpc_tools(self):
        with tempfile.TemporaryDirectory() as td:
            project = str(Path(__file__).resolve().parents[1])
            script = f"import os, sys; sys.path.insert(0, {project!r}); os.chdir(sys.argv[1]); from auto_kb.mcp_server import handle; from auto_kb.store import KnowledgeStore; s=KnowledgeStore('.'); s.init(); print(handle({{'id':1,'method':'tools/list'}}, s))"
            proc = run_python(["-c", script, td], check=True)
            self.assertIn("kb.search", proc.stdout)
            self.assertIn("kb.candidate_status", proc.stdout)

    def test_mcp_candidate_status_tool(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            store.init()
            task = store.create_task("MCP 候选状态测试", "verify candidate status tool")
            cid = store.stage_candidate("MCP can reject candidate", "discussion", evidence="unit test", source_task=task)
            from auto_kb.mcp_server import handle

            result = handle({"id": 1, "method": "tools/call", "params": {"name": "kb.candidate_status", "arguments": {"id": cid, "status": "rejected", "note": "unit test"}}}, store)
            self.assertNotIn("error", result)
            self.assertEqual(store.get_candidate(cid).status, "rejected")

    def test_cli_workflow_command(self):
        with tempfile.TemporaryDirectory() as td:
            proc = run_python(["-m", "auto_kb.cli", "--root", td, "workflow", "--title", "cli", "--goal", "cli evidence", "--conclusion", "cli publishes knowledge"])
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn('"pass": true', proc.stdout.lower())

    def test_cli_uses_auto_kb_root_from_other_cwd(self):
        with tempfile.TemporaryDirectory() as root_td, tempfile.TemporaryDirectory() as cwd_td:
            store = KnowledgeStore(root_td)
            store.init()
            task = store.create_task("AUTO_KB_ROOT test", "verify root lookup")
            cid = store.stage_candidate("AUTO_KB_ROOT lets CLI run outside the repository", "runbook", evidence="unit test", source_task=task)
            store.publish_candidate(cid)
            proc = run_python(
                ["-m", "auto_kb.cli", "search", "AUTO_KB_ROOT"],
                cwd=cwd_td,
                env_overrides={
                    "AUTO_KB_ROOT": root_td,
                    "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
                },
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("AUTO_KB_ROOT lets CLI run outside the repository", proc.stdout)


if __name__ == "__main__":
    unittest.main()
