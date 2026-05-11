from __future__ import annotations

import base64
import json
import subprocess
from dataclasses import dataclass

REPO_CHUNK_SIZE = 25
GRAPHQL_REPO_CHUNK_SIZE = 20


class GhError(RuntimeError):
    pass


@dataclass
class Gh:
    executable: str = "gh"

    def run_text(self, args: list[str]) -> str:
        completed = subprocess.run(
            [self.executable, *args],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if completed.returncode != 0:
            raise GhError(completed.stderr.strip() or completed.stdout.strip())
        return completed.stdout

    def run_json(self, args: list[str]) -> object:
        text = self.run_text(args).strip()
        if not text:
            return None
        return json.loads(text)

    def run_json_pages(self, args: list[str]) -> list[object]:
        text = self.run_text(args).strip()
        if not text:
            return []
        decoder = json.JSONDecoder()
        idx = 0
        values = []
        while idx < len(text):
            value, next_idx = decoder.raw_decode(text, idx)
            values.append(value)
            idx = next_idx
            while idx < len(text) and text[idx].isspace():
                idx += 1
        return values

    def search_issues(self, query: str, repos: list[str], owners: list[str], limit: int, prs: bool = False) -> list[dict]:
        if repos:
            return self._chunked_search_issues(query, repos, limit, prs=prs)
        args = [
            "search",
            "prs" if prs else "issues",
            _with_all_states(query),
            "--limit",
            str(limit),
            "--json",
            "number,title,url,state,repository,updatedAt",
        ]
        for owner in owners:
            args.extend(["--owner", owner])
        data = self.run_json(args)
        return list(data or [])

    def _chunked_search_issues(self, query: str, repos: list[str], limit: int, prs: bool = False) -> list[dict]:
        results: list[dict] = []
        for start in range(0, len(repos), REPO_CHUNK_SIZE):
            if len(results) >= limit:
                break
            chunk = repos[start : start + REPO_CHUNK_SIZE]
            args = [
                "search",
                "prs" if prs else "issues",
                _with_all_states(query),
                "--limit",
                str(max(1, limit - len(results))),
                "--json",
                "number,title,url,state,repository,updatedAt",
            ]
            for repo in chunk:
                args.extend(["--repo", repo])
            data = self.run_json(args)
            results.extend(list(data or []))
        return results[:limit]

    def search_issues_graphql(
        self,
        query: str,
        repos: list[str],
        owners: list[str],
        limit: int,
        mode: str,
        prs: bool = False,
    ) -> list[dict]:
        search_type = {
            "semantic": "ISSUE_SEMANTIC",
            "hybrid": "ISSUE_HYBRID",
        }.get(mode)
        if not search_type:
            return self.search_issues(query, repos, owners, limit, prs=prs)
        if repos:
            return self._chunked_search_issues_graphql(query, repos, limit, search_type, prs=prs)
        qualified_query = _qualify_query(query, repos=[], owners=owners)
        return self._graphql_issue_search(qualified_query, limit, search_type, prs=prs)

    def _chunked_search_issues_graphql(
        self,
        query: str,
        repos: list[str],
        limit: int,
        search_type: str,
        prs: bool = False,
    ) -> list[dict]:
        results: list[dict] = []
        for start in range(0, len(repos), GRAPHQL_REPO_CHUNK_SIZE):
            if len(results) >= limit:
                break
            chunk = repos[start : start + GRAPHQL_REPO_CHUNK_SIZE]
            qualified_query = _qualify_query(query, repos=chunk, owners=[])
            results.extend(self._graphql_issue_search(qualified_query, limit - len(results), search_type, prs=prs))
        return results[:limit]

    def _graphql_issue_search(self, query: str, limit: int, search_type: str, prs: bool = False) -> list[dict]:
        graphql = """
query($q: String!, $first: Int!, $type: SearchType!) {
  search(query: $q, type: $type, first: $first) {
    nodes {
      ... on Issue {
        __typename
        number
        title
        url
        state
        updatedAt
        repository { nameWithOwner }
      }
      ... on PullRequest {
        __typename
        number
        title
        url
        state
        updatedAt
        repository { nameWithOwner }
      }
    }
  }
}
"""
        data = self.run_json(["api", "graphql", "-f", f"query={graphql}", "-F", f"q={query}", "-F", f"first={limit}", "-F", f"type={search_type}"])
        nodes = (((data or {}).get("data") or {}).get("search") or {}).get("nodes") or []
        wanted = "PullRequest" if prs else "Issue"
        return [_graphql_node_to_search_item(node) for node in nodes if node.get("__typename") == wanted]

    def accessible_repos(self) -> list[dict]:
        pages = self.run_json_pages(
            [
                "api",
                "--method",
                "GET",
                "user/repos",
                "-F",
                "affiliation=owner,collaborator,organization_member",
                "-F",
                "per_page=100",
                "--paginate",
            ]
        )
        repos: list[dict] = []
        for page in pages:
            if isinstance(page, list):
                repos.extend(item for item in page if isinstance(item, dict))
        return repos

    def search_code(self, query: str, repos: list[str], owners: list[str], limit: int) -> list[dict]:
        if repos:
            return self._chunked_search_code(query, repos, limit)
        args = ["search", "code", query, "--limit", str(limit), "--json", "path,repository,url,textMatches"]
        for owner in owners:
            args.extend(["--owner", owner])
        data = self.run_json(args)
        return list(data or [])

    def _chunked_search_code(self, query: str, repos: list[str], limit: int) -> list[dict]:
        results: list[dict] = []
        for start in range(0, len(repos), REPO_CHUNK_SIZE):
            if len(results) >= limit:
                break
            chunk = repos[start : start + REPO_CHUNK_SIZE]
            args = [
                "search",
                "code",
                query,
                "--limit",
                str(max(1, limit - len(results))),
                "--json",
                "path,repository,url,textMatches",
            ]
            for repo in chunk:
                args.extend(["--repo", repo])
            data = self.run_json(args)
            results.extend(list(data or []))
        return results[:limit]

    def search_repos(self, query: str, owners: list[str], limit: int) -> list[dict]:
        args = ["search", "repos", query, "--limit", str(limit), "--json", "fullName,description,url,visibility,updatedAt"]
        for owner in owners:
            args.extend(["--owner", owner])
        data = self.run_json(args)
        return list(data or [])

    def list_repos(self, owner: str, limit: int) -> list[dict]:
        data = self.run_json(["repo", "list", owner, "--limit", str(limit), "--json", "nameWithOwner,description,url,visibility"])
        return list(data or [])

    def view_issue(self, repo: str, number: int, pr: bool = False) -> dict:
        args = ["pr" if pr else "issue", "view", str(number), "--repo", repo, "--json", "number,title,state,url,body"]
        data = self.run_json(args)
        if not isinstance(data, dict):
            raise GhError("GitHub CLI returned an unexpected issue shape")
        return data

    def file_content(self, repo: str, path: str, ref: str | None = None) -> str:
        endpoint = f"repos/{repo}/contents/{path}"
        if ref:
            endpoint = f"{endpoint}?ref={ref}"
        data = self.run_json(["api", endpoint])
        if not isinstance(data, dict) or "content" not in data:
            raise GhError("GitHub API returned an unexpected file shape")
        encoded = str(data["content"]).replace("\n", "")
        return base64.b64decode(encoded).decode("utf-8", errors="replace")


def _qualify_query(query: str, repos: list[str], owners: list[str]) -> str:
    qualifiers = [f"repo:{repo}" for repo in repos] + [f"owner:{owner}" for owner in owners]
    if not qualifiers:
        return query
    return f"{query} {' '.join(qualifiers)}"


def _with_all_states(query: str) -> str:
    lowered = query.lower()
    state_terms = ("is:open", "is:closed", "state:open", "state:closed")
    if any(term in lowered for term in state_terms):
        return query
    return f"{query} is:open is:closed"


def _graphql_node_to_search_item(node: dict) -> dict:
    return {
        "number": node.get("number"),
        "title": node.get("title", ""),
        "url": node.get("url", ""),
        "state": str(node.get("state", "")).lower(),
        "updatedAt": node.get("updatedAt", ""),
        "repository": {"nameWithOwner": (node.get("repository") or {}).get("nameWithOwner", "")},
    }
