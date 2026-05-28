from __future__ import annotations

import importlib
import unittest


class DashboardSmokeTest(unittest.TestCase):
    def test_dashboard_module_import(self) -> None:
        try:
            importlib.import_module("dashboard.app")
        except ModuleNotFoundError as exc:
            if exc.name == "streamlit":
                self.skipTest("streamlit not installed in test environment")
            raise


if __name__ == "__main__":
    unittest.main()
