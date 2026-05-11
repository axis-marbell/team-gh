import unittest

from team_gh.gh import _qualify_query, _state_queries


class GhTests(unittest.TestCase):
    def test_qualify_query_adds_repos_and_owners(self):
        query = _qualify_query("agent memory", repos=["one/repo"], owners=["team"])
        self.assertEqual(query, "agent memory repo:one/repo owner:team")

    def test_state_queries_adds_open_and_closed_by_default(self):
        self.assertEqual(_state_queries("agent memory"), ["agent memory is:open", "agent memory is:closed"])

    def test_state_queries_preserves_explicit_state(self):
        self.assertEqual(_state_queries("agent memory is:open"), ["agent memory is:open"])

    def test_state_queries_adds_merged_for_prs(self):
        self.assertEqual(
            _state_queries("agent memory", prs=True),
            ["agent memory is:open", "agent memory is:closed", "agent memory is:merged"],
        )

    def test_qualify_query_does_not_inject_state_qualifiers(self):
        query = _qualify_query("semantic memory", repos=["one/repo"], owners=[])
        self.assertNotIn("is:open", query)
        self.assertNotIn("is:closed", query)


if __name__ == "__main__":
    unittest.main()
