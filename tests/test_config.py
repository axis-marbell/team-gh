from pathlib import Path
import unittest

from team_gh.config import load_config


class ConfigTests(unittest.TestCase):
    def test_load_config_defaults_when_missing(self):
        path = Path(self._testMethodName) / "missing.toml"
        config = load_config(str(path))
        self.assertEqual(config.owners, ())
        self.assertEqual(config.repos, ())
        self.assertEqual(config.exclude_repos, ())
        self.assertEqual(config.limit, 8)

    def test_load_config_reads_defaults(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                """
[defaults]
limit = 3
owners = ["example-org"]
repos = ["example-org/example-repo"]
exclude_repos = ["example-org/example-archive"]
""",
                encoding="utf-8",
            )
            config = load_config(str(path))
        self.assertEqual(config.limit, 3)
        self.assertEqual(config.owners, ("example-org",))
        self.assertEqual(config.repos, ("example-org/example-repo",))
        self.assertEqual(config.exclude_repos, ("example-org/example-archive",))


if __name__ == "__main__":
    unittest.main()
