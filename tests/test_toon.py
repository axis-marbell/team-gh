import unittest

from team_gh.toon import render_search, scalar


class ToonTests(unittest.TestCase):
    def test_scalar_quotes_spaces_and_escapes_quotes(self):
        self.assertEqual(scalar('hello "team"'), '"hello \\"team\\""')

    def test_render_search_is_toon_like(self):
        text = render_search(
            "alpha beta",
            "all",
            "repos=1 owners=0 kinds=issues",
            [
                {
                    "kind": "issue",
                    "repo": "owner/repo",
                    "ref": "#1",
                    "title": "A result",
                    "action": "team-gh show owner/repo#1",
                }
            ],
            8,
        )
        self.assertTrue(text.startswith("team_gh_search\n"))
        self.assertIn("  result[1]\n", text)
        self.assertIn("    repo: owner/repo\n", text)
        self.assertNotIn("{", text)
        self.assertIn("  truncated: false\n", text)


if __name__ == "__main__":
    unittest.main()
