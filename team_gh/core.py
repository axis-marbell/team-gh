from __future__ import annotations

import math
import re

from .gh import Gh, GhError
from .toon import one_line

TARGET_RE = re.compile(r"^(?P<repo>[^#\s]+/[^#\s]+)#(?P<number>\d+)$")


def merged_repos(config_repos: tuple[str, ...], arg_repos: list[str] | None) -> list[str]:
    return list(arg_repos or config_repos)


def merged_owners(config_owners: tuple[str, ...], arg_owners: list[str] | None) -> list[str]:
    return list(arg_owners or config_owners)


def search(
    gh: Gh,
    query: str,
    scope: str,
    repos: list[str],
    owners: list[str],
    limit: int,
    repo_catalog: list[dict] | None = None,
    issue_search_mode: str = "lexical",
) -> tuple[str, list[dict]]:
    kinds = ["issues", "prs", "code", "repos"] if scope == "all" else [scope]
    per_kind = max(1, math.ceil(limit / len(kinds)))
    results: list[dict] = []
    for kind in kinds:
        if len(results) >= limit:
            break
        remaining = limit - len(results)
        count = min(per_kind, remaining)
        if kind == "issues":
            results.extend(
                _issue_results(
                    gh.search_issues_graphql(query, repos, owners, count, issue_search_mode, prs=False),
                    pr=False,
                    mode=issue_search_mode,
                )
            )
        elif kind == "prs":
            results.extend(
                _issue_results(
                    gh.search_issues_graphql(query, repos, owners, count, issue_search_mode, prs=True),
                    pr=True,
                    mode=issue_search_mode,
                )
            )
        elif kind == "code":
            results.extend(_code_results(gh.search_code(query, repos, owners, count)))
        elif kind == "repos":
            if repo_catalog is not None:
                results.extend(_repo_catalog_results(query, repo_catalog, count))
            else:
                results.extend(_repo_results(gh.search_repos(query, owners, count)))
        else:
            raise ValueError(f"unknown scope: {scope}")
    searched = f"repos={len(repos)} owners={len(owners)} kinds={','.join(kinds)} issue_search={issue_search_mode}"
    return searched, results[:limit]


def _issue_results(items: list[dict], pr: bool, mode: str = "lexical") -> list[dict]:
    kind = "pr" if pr else "issue"
    output = []
    for item in items:
        repo = item.get("repository", {}).get("nameWithOwner", "")
        number = item.get("number")
        output.append(
            {
                "kind": kind,
                "repo": repo,
                "ref": f"#{number}",
                "title": item.get("title", ""),
                "state": item.get("state", ""),
                "updated": item.get("updatedAt", ""),
                "url": item.get("url", ""),
                "why": f"Matched {kind} title/body/comments through GitHub {mode} search.",
                "action": f"team-gh show {repo}#{number}",
            }
        )
    return output


def _code_results(items: list[dict]) -> list[dict]:
    output = []
    for item in items:
        repo = item.get("repository", {}).get("nameWithOwner", "")
        path = item.get("path", "")
        matches = []
        for match in item.get("textMatches", [])[:2]:
            fragment = one_line(match.get("fragment", ""), limit=180)
            prop = match.get("property", "content")
            matches.append(f"{prop}: {fragment}")
        output.append(
            {
                "kind": "file",
                "repo": repo,
                "path": path,
                "url": item.get("url", ""),
                "why": "Matched file path/content through GitHub code search.",
                "matches": matches,
                "action": f"team-gh show {repo} {path}",
            }
        )
    return output


def _repo_results(items: list[dict]) -> list[dict]:
    output = []
    for item in items:
        output.append(
            {
                "kind": "repo",
                "repo": item.get("fullName", ""),
                "title": item.get("description", ""),
                "state": item.get("visibility", ""),
                "updated": item.get("updatedAt", ""),
                "url": item.get("url", ""),
                "why": "Matched repository metadata through GitHub repo search.",
                "action": f"team-gh repos --owner {item.get('fullName', '').split('/')[0]}",
            }
        )
    return output


def _repo_catalog_results(query: str, items: list[dict], limit: int) -> list[dict]:
    terms = [term.lower() for term in query.split() if term.strip()]
    output = []
    for item in items:
        haystack = f"{item.get('name', '')} {item.get('description', '')}".lower()
        if terms and not all(term in haystack for term in terms):
            continue
        name = item.get("name", "")
        output.append(
            {
                "kind": "repo",
                "repo": name,
                "title": item.get("description", ""),
                "state": item.get("visibility", ""),
                "url": item.get("url", ""),
                "why": "Matched authenticated repo cache metadata.",
                "action": f"team-gh repos --owner {name.split('/')[0]}",
            }
        )
        if len(output) >= limit:
            break
    return output


def parse_target(target: str) -> tuple[str, int]:
    match = TARGET_RE.match(target)
    if not match:
        raise ValueError("target must look like owner/repo#123")
    return match.group("repo"), int(match.group("number"))


def excerpt_text(text: str, max_chars: int = 1800) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."


def line_excerpt(text: str, spec: str | None, default_limit: int = 80) -> tuple[str, str]:
    lines = text.splitlines()
    if not lines:
        return "1:0", ""
    start = 1
    end = min(len(lines), default_limit)
    if spec:
        raw_start, _, raw_end = spec.partition(":")
        start = max(1, int(raw_start))
        end = min(len(lines), int(raw_end) if raw_end else start + default_limit - 1)
    selected = lines[start - 1 : end]
    return f"{start}:{end}", "\n".join(selected)


def show_issue_or_pr(gh: Gh, target: str) -> tuple[str, dict, list[dict]]:
    repo, number = parse_target(target)
    try:
        item = gh.view_issue_ref(repo, number)
    except GhError as exc:
        if _is_not_found_error(exc):
            raise ValueError(f"issue or PR #{number} not found in {repo}") from exc
        raise
    kind = "pr" if item.get("pull_request") else "issue"
    if kind == "pr":
        item = _prefer_pr_view(gh, repo, number, item)
    source = {
        "repo": repo,
        "ref": f"#{number}",
        "title": item.get("title", ""),
        "state": str(item.get("state", "")).lower(),
        "url": item.get("html_url") or item.get("url", ""),
    }
    body = excerpt_text(item.get("body", "") or "")
    excerpts = [{"section": "body", "text": body or "(empty body)"}]
    return kind, source, excerpts


def _prefer_pr_view(gh: Gh, repo: str, number: int, fallback: dict) -> dict:
    try:
        item = gh.view_issue(repo, number, pr=True)
    except GhError:
        return {
            "title": fallback.get("title", ""),
            "state": fallback.get("state", ""),
            "url": fallback.get("html_url", ""),
            "body": fallback.get("body", ""),
        }
    return {
        "title": item.get("title", ""),
        "state": str(item.get("state", "")).lower(),
        "url": item.get("url", ""),
        "body": item.get("body", ""),
    }


def _is_not_found_error(exc: GhError) -> bool:
    text = str(exc).lower()
    return "not found" in text or "could not resolve" in text or "404" in text


def show_file(gh: Gh, repo: str, path: str, lines: str | None = None, ref: str | None = None) -> tuple[str, dict, list[dict]]:
    content = gh.file_content(repo, path, ref=ref)
    line_range, text = line_excerpt(content, lines)
    source = {"repo": repo, "path": path, "url": f"https://github.com/{repo}/blob/{ref or 'HEAD'}/{path}"}
    excerpts = [{"section": "file", "lines": line_range, "text": excerpt_text(text)}]
    return "file", source, excerpts
