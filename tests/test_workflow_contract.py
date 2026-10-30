from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github" / "workflows" / "cas-race.yml").read_text(encoding="utf-8")
WORKER = (ROOT / "scripts" / "cas_worker.py").read_text(encoding="utf-8")


class WorkflowContractTests(unittest.TestCase):
    def test_only_manual_trigger_is_declared(self):
        trigger = WORKFLOW.split("permissions:", 1)[0]
        event_lines = re.findall(r"^  ([a-z_]+):\s*$", trigger, flags=re.MULTILINE)
        self.assertEqual(event_lines, ["workflow_dispatch"])

    def test_default_permissions_are_read_only_and_only_two_writer_jobs_get_write(self):
        self.assertIn("permissions:\n  contents: read\n  actions: read", WORKFLOW)
        self.assertEqual(WORKFLOW.count("      contents: write"), 2)
        self.assertNotIn("contents: write", WORKFLOW.split("jobs:", 1)[0])

    def test_three_standard_jobs_have_three_minute_limits(self):
        self.assertEqual(WORKFLOW.count("runs-on: ubuntu-24.04"), 3)
        self.assertEqual(WORKFLOW.count("timeout-minutes: 3"), 3)
        self.assertIn("needs: [writer_a, writer_b]", WORKFLOW)

    def test_no_third_party_actions_or_automatic_triggers(self):
        self.assertNotRegex(WORKFLOW, r"(?m)^\s+uses:")
        self.assertNotRegex(WORKFLOW, r"(?m)^  (push|pull_request|schedule|workflow_run):")

    def test_exactly_one_nonforced_git_push_call_exists(self):
        self.assertEqual(WORKER.count('"push", "--porcelain"'), 1)
        self.assertNotIn('"--force"', WORKER)
        self.assertIn('f"{args.candidate_sha}:refs/heads/{BRANCH}"', WORKER)

    def test_writer_jobs_require_distinct_ids_and_overlap(self):
        self.assertIn('a["runner_id"] != b["runner_id"]', WORKER)
        self.assertIn('max(starts.values()) < min(ends.values())', WORKER)
        self.assertIn("GitHub job timestamps do not prove overlapping writer race windows", WORKER)


if __name__ == "__main__":
    unittest.main()
