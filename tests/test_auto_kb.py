from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from auto_kb.store import KnowledgeStore
from auto_kb.workflow import KnowledgeClosureWorkflow


class AutoKBTests(unittest.TestCase):
    def test_task_quartet_and_preflight(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            store.init()
            task = store.create_task("证据测试", "需要 evidence 的任务")
            result = store.preflight(task, "需要 evidence 的任务")
            self.assertEqual(result["gate"], "NEEDS-REVIEW")
            for name in ["goal.md", "plan.md", "preflight.md", "log.md"]:
                self.assertTrue((Path(td) / "tasks" / task / name).exists())
            self.assertTrue(any("pitfalls" in h["path"] for h in result["hits"]))

    def test_stage_publish_and_gate(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            store.init()
            task = store.create_task("闭环测试", "测试知识闭环")
            store.preflight(task, "测试知识闭环")
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

    def test_workflow_without_conclusion_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            result = KnowledgeClosureWorkflow(td).run("无结论流程", "测试没有稳定结论时不能发布占位知识")
            self.assertFalse(result.gate["pass"])
            self.assertFalse(result.published)
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
            proc = subprocess.run([sys.executable, "-c", script, td], text=True, capture_output=True, check=True)
            self.assertIn("kb.search", proc.stdout)

    def test_cli_workflow_command(self):
        with tempfile.TemporaryDirectory() as td:
            proc = subprocess.run([sys.executable, "-m", "auto_kb.cli", "--root", td, "workflow", "--title", "cli", "--goal", "cli evidence", "--conclusion", "cli publishes knowledge"], text=True, capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn('"pass": true', proc.stdout.lower())


if __name__ == "__main__":
    unittest.main()

