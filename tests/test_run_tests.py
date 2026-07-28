from __future__ import annotations

import unittest
from unittest import mock

from scripts import run_tests


class RunTestsScriptTests(unittest.TestCase):
    def invoke(self, arguments: list[str]) -> tuple[int, int]:
        result = mock.Mock()
        result.wasSuccessful.return_value = True
        runner = mock.Mock()
        runner.run.return_value = result
        with (
            mock.patch.object(run_tests.unittest.defaultTestLoader, "discover", return_value=object()),
            mock.patch.object(run_tests.unittest, "TextTestRunner", return_value=runner) as constructor,
        ):
            exit_code = run_tests.main(arguments)
        return exit_code, constructor.call_args.kwargs["verbosity"]

    def test_default_output_is_compact(self) -> None:
        self.assertEqual(self.invoke([]), (0, 1))

    def test_verbose_flag_restores_per_test_output(self) -> None:
        self.assertEqual(self.invoke(["--verbose"]), (0, 2))


if __name__ == "__main__":
    unittest.main()
