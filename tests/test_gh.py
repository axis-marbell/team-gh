import unittest

from team_gh.gh import _qualify_query, _with_all_states


class GhTests(unittest.TestCase):
    def test_qualify_query_adds_repos_and_owners(self):
        query = _qualify_query("agent memory", repos=["one/repo"], owners=["team"])
        self.assertEqual(query, "agent memory repo:one/repo owner:team")

    def test_with_all_states_adds_open_and_closed_by_default(self):
        self.assertEqual(_with_all_states("agent memory"), "agent memory is:open is:closed")

    def test_with_all_states_preserves_explicit_state(self):
        self.assertEqual(_with_all_states("agent memory is:open"), "agent memory is:open")


if __name__ == "__main__":
    unittest.main()
