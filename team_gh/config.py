from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class Config:
    owners: tuple[str, ...] = ()
    repos: tuple[str, ...] = ()
    exclude_repos: tuple[str, ...] = ()
    limit: int = 8
    cache_ttl_seconds: int = 3600
    repo_cache_path: Path | None = None


def default_config_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "team-gh" / "config.toml"
    return Path.home() / ".config" / "team-gh" / "config.toml"


def config_path(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser()
    env_path = os.environ.get("TEAM_GH_CONFIG")
    if env_path:
        return Path(env_path).expanduser()
    return default_config_path()


def load_config(explicit: str | None = None) -> Config:
    path = config_path(explicit)
    if not path.exists():
        return Config()
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    defaults = data.get("defaults", {})
    owners = tuple(str(item) for item in defaults.get("owners", []))
    repos = tuple(str(item) for item in defaults.get("repos", []))
    exclude_repos = tuple(str(item) for item in defaults.get("exclude_repos", []))
    limit = int(defaults.get("limit", 8))
    cache_ttl_seconds = int(defaults.get("cache_ttl_seconds", 3600))
    repo_cache = defaults.get("repo_cache_path")
    repo_cache_path = Path(str(repo_cache)).expanduser() if repo_cache else None
    return Config(
        owners=owners,
        repos=repos,
        exclude_repos=exclude_repos,
        limit=limit,
        cache_ttl_seconds=cache_ttl_seconds,
        repo_cache_path=repo_cache_path,
    )


def default_cache_path() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / "team-gh" / "repos.json"
    return Path.home() / ".cache" / "team-gh" / "repos.json"
