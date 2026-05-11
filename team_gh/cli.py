from __future__ import annotations

import argparse
import sys

from .config import load_config
from .core import search, show_file, show_issue_or_pr
from .gh import Gh, GhError
from .repo_cache import load_or_refresh_repos, repo_names
from .toon import render_repos, render_search, render_show


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="team-gh", description="TOON-shaped progressive GitHub search for agent teams")
    parser.add_argument("--config", help="Path to local config TOML")
    sub = parser.add_subparsers(dest="command", required=True)

    search_parser = sub.add_parser("search", help="Search GitHub and return compact TOON results")
    search_parser.add_argument("query", nargs="+")
    search_parser.add_argument("--scope", choices=["all", "issues", "prs", "code", "repos"], default="all")
    search_parser.add_argument("--owner", action="append", default=None, help="Owner/org to search; repeatable")
    search_parser.add_argument("--repo", action="append", default=None, help="Repository owner/name to search; repeatable")
    search_parser.add_argument("--limit", type=int, default=None)
    search_parser.add_argument("--refresh-repos", action="store_true", help="Refresh authenticated repo cache before searching")
    search_parser.add_argument(
        "--issue-search",
        choices=["lexical", "semantic", "hybrid"],
        default="lexical",
        help="Issue/PR search mode. semantic/hybrid use GitHub GraphQL SearchType modes.",
    )

    show_parser = sub.add_parser("show", help="Show a bounded source excerpt")
    show_parser.add_argument("target", help="owner/repo#123 or owner/repo for file mode")
    show_parser.add_argument("path", nargs="?", help="File path when target is owner/repo")
    show_parser.add_argument("--lines", help="Line range like 10:80 for file mode")
    show_parser.add_argument("--ref", help="Git ref for file mode")

    repos_parser = sub.add_parser("repos", help="List repositories visible for configured or passed owners")
    repos_parser.add_argument("--owner", action="append", default=None, help="Owner/org to list; repeatable")
    repos_parser.add_argument("--limit", type=int, default=None)
    repos_parser.add_argument("--refresh", action="store_true", help="Refresh authenticated repo cache before listing")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)
    gh = Gh()
    try:
        if args.command == "search":
            query = " ".join(args.query)
            limit = args.limit or config.limit
            repos = list(args.repo or ())
            owners = list(args.owner or ())
            repo_catalog = None
            if not repos and not owners:
                repo_catalog = load_or_refresh_repos(gh, config, refresh=args.refresh_repos)
                repos = repo_names(repo_catalog, config.exclude_repos)
                if config.exclude_repos:
                    excluded = set(config.exclude_repos)
                    repo_catalog = [repo for repo in repo_catalog if repo.get("name") not in excluded]
            searched, results = search(
                gh,
                query,
                args.scope,
                repos,
                owners,
                limit,
                repo_catalog=repo_catalog,
                issue_search_mode=args.issue_search,
            )
            sys.stdout.write(render_search(query, args.scope, searched, results, limit))
            return 0
        if args.command == "show":
            if args.path:
                kind, source, excerpts = show_file(gh, args.target, args.path, lines=args.lines, ref=args.ref)
            else:
                kind, source, excerpts = show_issue_or_pr(gh, args.target)
            sys.stdout.write(render_show(kind, source, excerpts))
            return 0
        if args.command == "repos":
            limit = args.limit or config.limit
            owners = list(args.owner or ())
            if owners:
                repos = []
                for owner in owners:
                    repos.extend(
                        {
                            "name": item.get("nameWithOwner", ""),
                            "visibility": item.get("visibility", ""),
                            "description": item.get("description", ""),
                            "url": item.get("url", ""),
                        }
                        for item in gh.list_repos(owner, limit)
                    )
            else:
                repos = load_or_refresh_repos(gh, config, refresh=args.refresh)
                if config.exclude_repos:
                    excluded = set(config.exclude_repos)
                    repos = [repo for repo in repos if repo.get("name") not in excluded]
            sys.stdout.write(render_repos(repos[:limit], limit))
            return 0
    except (GhError, ValueError) as exc:
        sys.stderr.write(f"team-gh error: {exc}\n")
        return 2
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
