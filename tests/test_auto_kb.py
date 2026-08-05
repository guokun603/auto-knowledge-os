from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import os
from pathlib import Path

os.environ.setdefault("AUTO_KB_DISABLE_EXTERNAL", "1")

from auto_kb.store import KnowledgeStore, MAX_RISK_HITS
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
            result = KnowledgeClosureWorkflow(td).run("工作流测试", "plain greenfield workflow", "工作流可以在无风险 preflight 时自动发布结论")
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
            # The goal must avoid vocabulary used by the seeded PIT-* pitfalls
            # (goal, plan, run, cli, preflight, evidence...), otherwise preflight
            # raises Required Actions and the gate correctly refuses to close.
            proc = run_python(["-m", "auto_kb.cli", "--root", td, "workflow", "--title", "cli", "--goal", "publish durable conclusion automatically", "--conclusion", "cli publishes knowledge"])
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


    def test_workflow_with_conclusion_does_not_auto_close_required_actions(self):
        with tempfile.TemporaryDirectory() as td:
            result = KnowledgeClosureWorkflow(td).run("工作流风险测试", "需要 evidence 的任务", "有结论也不能跳过历史坑复查")
            self.assertFalse(result.gate["pass"])
            self.assertFalse(result.published)
            self.assertIn("unresolved preflight required actions", " ".join(result.gate["errors"]))
            self.assertTrue(any(action["status"] == "pending" for action in result.preflight["required_actions"]))

    def test_accepted_candidate_publishes_instead_of_disappearing(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            store.init()
            task = store.create_task("accepted 候选测试", "verify accepted publishes")
            store.preflight(task, "verify accepted publishes")
            store.resolve_required_action(task, "all", "resolved", "unit test")
            store.add_evidence(task, "proof.txt", "proof")
            cid = store.stage_candidate("Accepted candidate writes Markdown", "runbook", evidence="unit test", source_task=task)
            cand = store.set_candidate_status(cid, "accepted", "unit test accepts it")
            self.assertEqual(cand.status, "accepted")
            self.assertTrue(cand.published_path)
            self.assertTrue((Path(td) / cand.published_path).exists())
            self.assertTrue(store.gate(task)["pass"])

    def test_publish_number_scans_existing_knowledge_files(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            store.init()
            existing = Path(td) / "knowledge" / "runbooks" / "KB-0042-existing.md"
            existing.write_text("# Existing\n\n## Conclusion\nExisting\n", encoding="utf-8")
            task = store.create_task("KB 编号测试", "verify numbering")
            cid = store.stage_candidate("Next KB number ignores sqlite id", "runbook", evidence="unit test", source_task=task)
            path = store.publish_candidate(cid)
            self.assertTrue(path.name.startswith("KB-0043-"), path.name)

    def test_duplicate_detection_crosses_knowledge_type_directories(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            store.init()
            existing = Path(td) / "knowledge" / "decisions" / "KB-0042-same-conclusion.md"
            existing.parent.mkdir(parents=True, exist_ok=True)
            existing.write_text("# Same Conclusion\n\n## Conclusion\nSame Conclusion\n", encoding="utf-8")
            task = store.create_task("跨目录查重测试", "verify duplicate search")
            cid = store.stage_candidate("Same Conclusion", "lesson", evidence="unit test", source_task=task)
            path = store.publish_candidate(cid)
            self.assertEqual(path, existing)
            self.assertEqual(store.get_candidate(cid).status, "duplicate")

    def test_resolve_required_action_note_does_not_stack(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            store.init()
            task = store.create_task("note 叠加测试", "需要 evidence 的任务")
            store.preflight(task, "需要 evidence 的任务")
            store.resolve_required_action(task, "RA-001", "needs-review", "first note")
            store.resolve_required_action(task, "RA-001", "resolved", "second note")
            preflight = (Path(td) / "tasks" / task / "preflight.md").read_text(encoding="utf-8")
            self.assertIn("second note", preflight)
            self.assertNotIn("first note -- second note", preflight)

    def test_init_does_not_revive_deleted_seed_files(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            store.init()
            seed = Path(td) / "knowledge" / "pitfalls" / "PIT-001-no-evidence-no-completion.md"
            self.assertTrue(seed.exists())
            seed.unlink()
            store.init()
            self.assertFalse(seed.exists())

    def test_search_does_not_match_two_character_chinese_fragments_only(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            store.init()
            weak = Path(td) / "knowledge" / "runbooks" / "KB-0040-weak.md"
            strong = Path(td) / "knowledge" / "runbooks" / "KB-0041-strong.md"
            weak.write_text("# 自动\n\n只有自动两个字\n", encoding="utf-8")
            strong.write_text("# 自动化\n\n包含完整自动化关键词\n", encoding="utf-8")
            hits = store.search("自动化", limit=5)
            paths = [hit["path"] for hit in hits]
            self.assertIn("knowledge\\runbooks\\KB-0041-strong.md", paths)
            self.assertNotIn("knowledge\\runbooks\\KB-0040-weak.md", paths)

    def test_mcp_server_entrypoint_uses_standard_stdio(self):
        entry = (Path(__file__).resolve().parents[1] / "mcp-server" / "server.py").read_text(encoding="utf-8")
        self.assertIn("stdio_main", entry)

    def test_preflight_caps_blocking_required_actions(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            store.init()
            pitfalls = Path(td) / "knowledge" / "pitfalls"
            for i in range(MAX_RISK_HITS + 2):
                (pitfalls / f"KB-01{i:02d}-widgetflux.md").write_text(
                    f"# Widgetflux pitfall {i}\n\nwidgetflux breaks when reused\n", encoding="utf-8"
                )
            task = store.create_task("上限测试", "widgetflux")
            result = store.preflight(task, "widgetflux")
            self.assertEqual(len(result["risk_hits"]), MAX_RISK_HITS)
            self.assertEqual(len(result["deferred_risks"]), 2)
            blocking = [a for a in result["required_actions"] if a["kind"] == "pitfall"]
            self.assertEqual(len(blocking), MAX_RISK_HITS)
            preflight_text = (Path(td) / "tasks" / task / "preflight.md").read_text(encoding="utf-8")
            self.assertIn("Deferred Risk Hits", preflight_text)

    def test_search_ignores_publish_template_scaffolding(self):
        with tempfile.TemporaryDirectory() as td:
            store = KnowledgeStore(td)
            store.init()
            task = store.create_task("模板噪音测试", "verify scaffolding is ignored")
            cid = store.stage_candidate("Snowmelt cadence stays stable", "runbook", evidence="unit test", source_task=task)
            published = store.publish_candidate(cid)
            body = published.read_text(encoding="utf-8")
            self.assertIn("- type: runbook", body)
            self.assertIn("## Conclusion", body)
            self.assertEqual(store.search("type"), [])
            self.assertEqual(store.search("scope"), [])
            self.assertEqual(store.search("tags"), [])
            self.assertTrue(store.search("snowmelt"))


if __name__ == "__main__":
    unittest.main()


