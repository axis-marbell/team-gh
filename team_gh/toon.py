from __future__ import annotations

from collections.abc import Iterable


def one_line(value: object, limit: int = 220) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    if len(text) > limit:
        text = text[: max(0, limit - 3)].rstrip() + "..."
    return text


def scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    text = one_line(value)
    if text == "":
        return '""'
    safe = all(ch.isalnum() or ch in "-_./:#@+=,()" for ch in text)
    if safe:
        return text
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


class ToonWriter:
    def __init__(self) -> None:
        self._lines: list[str] = []

    def line(self, text: str = "", indent: int = 0) -> None:
        if text == "":
            self._lines.append("")
            return
        self._lines.append("  " * indent + text)

    def field(self, key: str, value: object, indent: int = 0) -> None:
        self.line(f"{key}: {scalar(value)}", indent)

    def block(self, name: str, indent: int = 0) -> None:
        self.line(name, indent)

    def render(self) -> str:
        return "\n".join(self._lines).rstrip() + "\n"


def render_search(query: str, scope: str, searched: str, results: Iterable[dict], limit: int) -> str:
    items = list(results)
    writer = ToonWriter()
    writer.block("team_gh_search")
    writer.field("query", query, 1)
    writer.field("scope", scope, 1)
    writer.field("searched", searched, 1)
    writer.field("returned", len(items), 1)
    writer.field("truncated", len(items) >= limit, 1)
    for idx, item in enumerate(items, start=1):
        writer.line("", 1)
        writer.block(f"result[{idx}]", 1)
        for key in ("kind", "repo", "ref", "path", "title", "state", "updated", "url", "why", "action"):
            if key in item and item[key] not in (None, ""):
                writer.field(key, item[key], 2)
        for match_idx, match in enumerate(item.get("matches", []), start=1):
            writer.field(f"match[{match_idx}]", match, 2)
    return writer.render()


def render_show(kind: str, source: dict, excerpts: Iterable[dict]) -> str:
    writer = ToonWriter()
    writer.block("team_gh_show")
    writer.field("source", "github", 1)
    writer.field("kind", kind, 1)
    for key in ("repo", "ref", "path", "title", "state", "url"):
        if key in source and source[key] not in (None, ""):
            writer.field(key, source[key], 1)
    for idx, excerpt in enumerate(excerpts, start=1):
        writer.line("", 1)
        writer.block(f"excerpt[{idx}]", 1)
        for key in ("section", "lines", "text"):
            if key in excerpt and excerpt[key] not in (None, ""):
                writer.field(key, excerpt[key], 2)
    return writer.render()


def render_repos(repos: Iterable[dict], limit: int) -> str:
    items = list(repos)
    writer = ToonWriter()
    writer.block("team_gh_repos")
    writer.field("returned", len(items), 1)
    writer.field("truncated", len(items) >= limit, 1)
    for idx, repo in enumerate(items, start=1):
        writer.line("", 1)
        writer.block(f"repo[{idx}]", 1)
        for key in ("name", "visibility", "description", "url"):
            if key in repo and repo[key] not in (None, ""):
                writer.field(key, repo[key], 2)
    return writer.render()
