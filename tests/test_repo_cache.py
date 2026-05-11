import tempfile
import unittest
from pathlib import Path

from team_gh.config import Config
from team_gh.repo_cache import load_or_refresh_repos, repo_names


class FakeGh:
    def __init__(self):
        self.calls = 0

    def accessible_repos(self):
        self.calls += 1
        return [
            {
                "full_name": "example-org/example-repo",
                "visibility": "public",
                "description": "Example",
                "html_url": "https://github.com/example-org/example-repo",
            }
        ]


class RepoCacheTests(unittest.TestCase):
    def test_load_or_refresh_repos_uses_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Config(repo_cache_path=Path(tmp) / "repos.json")
            gh = FakeGh()
            first = load_or_refresh_repos(gh, config)
            second = load_or_refresh_repos(gh, config)
        self.assertEqual(first, second)
        self.assertEqual(gh.calls, 1)

    def test_repo_names_excludes_repos(self):
        repos = [{"name": "a/one"}, {"name": "a/two"}]
        self.assertEqual(repo_names(repos, ("a/two",)), ["a/one"])


if __name__ == "__main__":
    unittest.main()
