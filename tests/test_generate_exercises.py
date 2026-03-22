import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import unittest

from scripts import generate_exercises


class GenerateExercisesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data_dir = Path(self.tmp.name)
        self.qq = "12345"
        self.student = "张三"
        self.subject = "math"

    def _write_result(self, batch_id, timestamp, weak_points):
        batch_dir = self.data_dir / self.qq / self.student / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "subject": self.subject,
            "timestamp": timestamp,
            "weak_points": weak_points,
        }
        (batch_dir / f"result_{self.subject}.json").write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )

    def test_collect_top_weak_points_filters_by_date_range(self):
        self._write_result("20260301_a", "2026-03-01T08:00:00", ["A", "A", "old"])
        self._write_result("20260315_b", "2026-03-15T08:00:00", ["B", "B", "mid"])
        self._write_result("20260325_c", "2026-03-25T08:00:00", ["C", "late"])

        result = generate_exercises.collect_top_weak_points(
            self.data_dir,
            self.qq,
            self.student,
            self.subject,
            start="2026-03-10",
            end="2026-03-20",
            limit=3,
        )

        self.assertEqual(result, ["B", "mid"])

    def test_collect_top_weak_points_uses_full_history_when_dates_missing(self):
        self._write_result("20260301_a", "2026-03-01T08:00:00", ["A", "A"])
        self._write_result("20260315_b", "2026-03-15T08:00:00", ["B"])
        self._write_result("20260325_c", "2026-03-25T08:00:00", ["C"])

        result = generate_exercises.collect_top_weak_points(
            self.data_dir,
            self.qq,
            self.student,
            self.subject,
            limit=3,
        )

        self.assertEqual(result, ["A", "B", "C"])

    def test_main_filters_weak_points_by_cli_date_range(self):
        self._write_result("20260301_a", "2026-03-01T08:00:00", ["old"])
        self._write_result("20260315_b", "2026-03-15T08:00:00", ["in_range"])
        self._write_result("20260325_c", "2026-03-25T08:00:00", ["late"])

        argv = [
            "generate_exercises.py",
            "--qq",
            self.qq,
            "--student",
            self.student,
            "--subject",
            self.subject,
            "--count",
            "2",
            "--start",
            "2026-03-10",
            "--end",
            "2026-03-20",
        ]

        with patch.object(generate_exercises, "DATA_DIR", str(self.data_dir)):
            with patch("sys.argv", argv):
                with patch("builtins.print") as mock_print:
                    generate_exercises.main()

        printed = [call.args[0] for call in mock_print.call_args_list]
        self.assertIn("以下是学生 张三 最需要提升的 math 核心薄弱点：", printed)
        self.assertIn("- in_range", printed)
        self.assertNotIn("- old", printed)
        self.assertNotIn("- late", printed)

    def test_main_propagates_unexpected_parse_errors(self):
        self._write_result("20260315_b", "2026-03-15T08:00:00", ["in_range"])

        argv = [
            "generate_exercises.py",
            "--qq",
            self.qq,
            "--student",
            self.student,
            "--subject",
            self.subject,
        ]

        def boom(*args, **kwargs):
            raise RuntimeError("boom")

        with patch.object(generate_exercises, "DATA_DIR", str(self.data_dir)):
            with patch("sys.argv", argv):
                with patch("scripts.generate_exercises.json.load", side_effect=boom):
                    with self.assertRaises(RuntimeError):
                        generate_exercises.main()


if __name__ == "__main__":
    unittest.main()
