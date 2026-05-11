from __future__ import annotations

import json
import time
from pathlib import Path

from .config import Config, default_cache_path
from .gh import Gh


def cache_path(config: Config) -> Path:
    return config.repo_cache_path or default_cache_path()


def load_or_refresh_repos(gh: Gh, config: Config, refresh: bool = False) -> list[dict]:
    path = cache_path(config)
    if not refresh and path.exists():
        age = time.time() - path.stat().st_mtime
        if age <= config.cache_ttl_seconds:
            return _read_cache(path)
    repos = gh.accessible_repos()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_compact_repos(repos), indent=2, sort_keys=True), encoding="utf-8")
    return _compact_repos(repos)


def _read_cache(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _compact_repos(repos: list[dict]) -> list[dict]:
    compact = []
    for repo in repos:
        full_name = repo.get("full_name") or repo.get("nameWithOwner")
        if not full_name:
            continue
        compact.append(
            {
                "name": full_name,
                "visibility": repo.get("visibility", "private" if repo.get("private") else "public"),
                "description": repo.get("description") or "",
                "url": repo.get("html_url") or repo.get("url") or f"https://github.com/{full_name}",
            }
        )
    compact.sort(key=lambda item: item["name"])
    return compact


def repo_names(repos: list[dict], exclude: tuple[str, ...] = ()) -> list[str]:
    excluded = set(exclude)
    return [repo["name"] for repo in repos if repo.get("name") and repo["name"] not in excluded]
