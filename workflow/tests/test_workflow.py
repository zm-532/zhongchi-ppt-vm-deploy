import unittest

from workflow.engine import WorkflowEngine, WorkflowStatus


PROJECT_INPUT = {
    "project_id": 1,
    "project_name": "某城市轨道交通声屏障改造项目",
    "product_line": "轨交既有线改造",
    "modules": [
        {"module_id": "M1", "uploaded_file_ids": [1], "status": "uploaded"},
        {"module_id": "M2", "uploaded_file_ids": [2], "status": "uploaded"},
        {"module_id": "M5", "uploaded_file_ids": [], "status": "pending"},
        {"module_id": "M6", "uploaded_file_ids": [], "status": "pending"},
    ],
}


class WorkflowEngineTest(unittest.TestCase):
    def test_run_until_review_executes_required_nodes_and_pauses(self):
        engine = WorkflowEngine(use_mock_llm=True, use_mock_embedding=True)

        state = engine.run_until_review(PROJECT_INPUT)

        self.assertEqual(state.status, WorkflowStatus.WAITING_REVIEW)
        self.assertEqual(
            state.completed_nodes,
            [
                "load_project",
                "prepare_modules",
                "parse_module_files",
                "extract_module_tags",
                "retrieve_module_assets",
                "match_cases",
                "generate_module_outlines",
                "human_review",
            ],
        )
        self.assertEqual([module.module_id for module in state.modules], ["M1", "M2", "M5", "M6"])
        self.assertTrue(all(module.status == "outlined" for module in state.modules))
        self.assertTrue(all(module.outline["slides"] for module in state.modules))
        self.assertTrue(state.mock_fallbacks["llm"])
        self.assertTrue(state.mock_fallbacks["embedding"])

    def test_resume_after_review_renders_chapters_and_merges_final_ppt(self):
        engine = WorkflowEngine(use_mock_llm=True, use_mock_embedding=True)
        state = engine.run_until_review(PROJECT_INPUT)

        final_state = engine.resume_after_review(state, approved=True)

        self.assertEqual(final_state.status, WorkflowStatus.FINISHED)
        self.assertEqual(final_state.completed_nodes[-3:], ["render_chapter_ppts", "merge_ppt", "quality_check"])
        self.assertEqual(final_state.final_ppt_path, "outputs/project_1/final_M1_M2_M5_M6.pptx")
        self.assertTrue(all(module.status == "rendered" for module in final_state.modules))
        self.assertEqual(
            [module.chapter_ppt_path for module in final_state.modules],
            [
                "outputs/project_1/M1_chapter.pptx",
                "outputs/project_1/M2_chapter.pptx",
                "outputs/project_1/M5_chapter.pptx",
                "outputs/project_1/M6_chapter.pptx",
            ],
        )

    def test_rejects_dynamic_modules_in_input(self):
        engine = WorkflowEngine()
        invalid_input = {
            **PROJECT_INPUT,
            "modules": PROJECT_INPUT["modules"] + [{"module_id": "M3", "uploaded_file_ids": [], "status": "pending"}],
        }

        with self.assertRaises(ValueError) as context:
            engine.run_until_review(invalid_input)

        self.assertIn("M1/M2/M5/M6", str(context.exception))

    def test_review_rejection_keeps_workflow_waiting(self):
        engine = WorkflowEngine()
        state = engine.run_until_review(PROJECT_INPUT)

        rejected = engine.resume_after_review(state, approved=False)

        self.assertEqual(rejected.status, WorkflowStatus.WAITING_REVIEW)
        self.assertEqual(rejected.completed_nodes[-1], "human_review_rejected")
        self.assertTrue(all(module.status == "outlined" for module in rejected.modules))


if __name__ == "__main__":
    unittest.main()
