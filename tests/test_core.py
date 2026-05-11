import unittest

from team_gh.core import line_excerpt, parse_target, search


class FakeGh:
    def search_issues_graphql(self, *args, **kwargs):
        return []

    def search_code(self, *args, **kwargs):
        return []

    def search_repos(self, *args, **kwargs):
        raise AssertionError("global repo search should not be used with repo_catalog")


class CoreTests(unittest.TestCase):
    def test_parse_target(self):
        self.assertEqual(parse_target("owner/repo#42"), ("owner/repo", 42))

    def test_line_excerpt_range(self):
        text = "\n".join(f"line {idx}" for idx in range(1, 11))
        line_range, excerpt = line_excerpt(text, "3:5")
        self.assertEqual(line_range, "3:5")
        self.assertEqual(excerpt, "line 3\nline 4\nline 5")

    def test_search_uses_repo_catalog_for_repo_scope(self):
        searched, results = search(
            FakeGh(),
            "search tool",
            "repos",
            ["example-org/search-tool"],
            [],
            5,
            repo_catalog=[
                {
                    "name": "example-org/search-tool",
                    "description": "Search tool",
                    "visibility": "private",
                    "url": "https://github.com/example-org/search-tool",
                }
            ],
            issue_search_mode="hybrid",
        )
        self.assertIn("repos=1", searched)
        self.assertIn("issue_search=hybrid", searched)
        self.assertEqual(results[0]["repo"], "example-org/search-tool")


if __name__ == "__main__":
    unittest.main()
