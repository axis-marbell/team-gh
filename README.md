# team-gh

`team-gh` is a small agent-facing GitHub search CLI. It wraps the authenticated
GitHub CLI and returns compact TOON-like output for progressive disclosure
across repositories, issues, pull requests, code, and markdown.

It is not an agent memory replacement. It is a discovery layer for finding the
source artifacts an agent should read before making a team-wide claim.

## Install

```bash
python -m pip install -e .
```

Requirements:

- Python 3.11+
- GitHub CLI `gh`
- an authenticated `gh` session with access to the repositories you want to
  search

## Commands

Search across every repository visible to the authenticated GitHub user. By
default, `--scope all` searches issues, pull requests, code, and repository
metadata. GitHub issue/PR search includes open and closed items unless you
explicitly narrow the query. Code search uses GitHub's indexed default branch;
for most team repositories that is `main`, but the legacy code search API does
not expose a branch selector.

```bash
team-gh search "residual output substrate ladder" --scope all --limit 8
```

The default search path discovers accessible repositories through `gh api`,
caches the compact repo list locally, and refreshes it when the cache is stale.
Use `--refresh-repos` to force a refresh.

Narrow a search when needed:

```bash
team-gh search "residual output" --repo owner/repo --scope issues
team-gh search "agent memory" --owner example-org --scope all
```

Show a bounded source excerpt for an issue or pull request:

```bash
team-gh show owner/repo#123
```

Show a bounded source excerpt for a file:

```bash
team-gh show owner/repo path/to/file.md --lines 40:120
```

List repositories visible to the authenticated GitHub user:

```bash
team-gh repos --limit 50 --refresh
```

## Output Shape

Search returns references and short matches:

```toon
team_gh_search
  query: "residual output substrate ladder"
  scope: all
  returned: 2
  truncated: false

  result[1]
    kind: issue
    repo: owner/repo
    ref: #123
    title: "Residual handling"
    state: open
    updated: 2026-05-11T12:00:00Z
    url: https://github.com/owner/repo/issues/123
    why: "Matched issue title/body/comments through GitHub search."
    action: team-gh show owner/repo#123
```

Use `team-gh show` to fetch source excerpts. Search output is intentionally
small so agents can decide what to expand.

## Progressive Disclosure

The CLI is designed around three disclosure levels:

1. `team-gh search` returns references, short matches, and follow-up actions.
2. `team-gh show` returns bounded source excerpts for one selected result.
3. Full source stays behind GitHub URLs or explicit file expansion.

This keeps default search output small enough for agents to scan without
turning every search into a large context dump.

## Configuration

`team-gh` reads configuration from the first available path:

1. `--config PATH`
2. `$TEAM_GH_CONFIG`
3. `$XDG_CONFIG_HOME/team-gh/config.toml`
4. `~/.config/team-gh/config.toml`

The config file is optional. By default, `team-gh` discovers repositories from
the authenticated `gh` user and stores a compact repo cache under the user cache
directory. Config is for preferences and exclusions, not for hardcoding a team
repo inventory.

Example:

```toml
[defaults]
limit = 8

cache_ttl_seconds = 3600

exclude_repos = [
  "example-org/example-archive"
]
```

Do not commit real private repository lists or tokens. `team-gh` does not need
tokens in its config because it delegates authentication to `gh`.

## Safety Notes

- Output is TOON-like text, not JSON or YAML.
- Search results are summaries and references, not the source of truth.
- Source-backed work should expand a result with `team-gh show` before acting.
- Config examples must use placeholders only.
