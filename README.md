# team-gh

`team-gh` is an agent-facing GitHub search CLI. It searches the repositories
visible to the authenticated GitHub CLI user and returns compact TOON-like
results for progressive disclosure across issues, pull requests, code, files,
markdown, and repository metadata.

It is not an agent memory replacement. It is a discovery layer for finding the
source artifacts an agent should read before making a team-wide claim.

## Install

```bash
pipx install -e . --force
```

Requirements:

- Python 3.11+
- GitHub CLI `gh`
- an authenticated `gh` session with access to the repositories you want to
  search

## Quick Start

Refresh the local repo cache and confirm the CLI can see your GitHub surface:

```bash
team-gh repos --limit 20 --refresh
```

Search every visible repository with compact output:

```bash
team-gh search "agent memory" --scope all --limit 8 --refresh-repos
```

Expand one result:

```bash
team-gh show example-org/example-repo#123
team-gh show example-org/example-repo README.md --lines 1:80
```

Narrow a search when you know the likely owner or repo:

```bash
team-gh search "residual output" --repo example-org/example-repo --scope all
team-gh search "agent onboarding" --owner example-org --scope issues
```

Use semantic or hybrid issue search for conceptual queries:

```bash
team-gh search "where did we discuss agent onboarding" --scope issues --issue-search hybrid
team-gh search "memory resolver design" --repo example-org/example-repo --scope prs --issue-search semantic
```

## Search Defaults

By default, `team-gh search` discovers all repositories visible to the
authenticated `gh` user, caches that compact repo list locally, and searches
that set. Use `--repo` or `--owner` to narrow the search.

`--scope all` searches:

- issues
- pull requests
- code/files on GitHub's indexed default branch
- repository metadata

Lexical issue/PR search explicitly adds `is:open is:closed` unless you provide
your own state qualifier. Semantic and hybrid issue search avoid state
qualifiers by default because GitHub's GraphQL semantic search already returns
open and closed issues/PRs, while `is:open is:closed` can suppress semantic
matches.

Code search uses GitHub's indexed default branch. For most team repositories
that is `main`, but the legacy code search API does not expose a branch
selector.

## Progressive Disclosure

The CLI is designed around three disclosure levels:

1. `team-gh search` returns references, short matches, and follow-up actions.
2. `team-gh show` returns bounded source excerpts for one selected result.
3. Full source stays behind GitHub URLs or explicit file expansion.

Start broad, then narrow. In local testing, all-repo searches are useful for
known words, file names, and repo metadata. Semantic/hybrid searches are most
useful after narrowing to a likely repo or owner, because very broad conceptual
queries can return sparse results through GitHub's semantic API.

## Output Shape

Search returns references and short matches:

```toon
team_gh_search
  query: "agent memory"
  scope: all
  searched: "repos=20 owners=0 kinds=issues,prs,code,repos issue_search=hybrid"
  returned: 2
  truncated: false

  result[1]
    kind: issue
    repo: example-org/example-repo
    ref: #123
    title: "Memory resolver design"
    state: open
    updated: 2026-05-11T12:00:00Z
    url: https://github.com/example-org/example-repo/issues/123
    why: "Matched issue title/body/comments through GitHub hybrid search."
    action: "team-gh show example-org/example-repo#123"
```

Use `team-gh show` to fetch source excerpts. Search output is intentionally
small so agents can decide what to expand.

## Self-Test For Agents

Every agent adopting this tool should run its own self-test and record the exact
commands that worked in its local instructions or skill.

Recommended self-test:

```bash
team-gh repos --limit 20 --refresh
team-gh search "README" --scope code --limit 8 --refresh-repos
team-gh search "agent memory" --scope all --limit 8 --issue-search hybrid
team-gh search "agent memory" --repo example-org/example-repo --scope all --issue-search hybrid
team-gh show example-org/example-repo#123
team-gh show example-org/example-repo README.md --lines 1:80
```

Replace the example repo and issue with real results from your own first search.
Do not copy another agent's private repo list into your config or docs.

After testing, the agent should update its own substrate:

- Add a short instruction to `AGENTS.md`, `CLAUDE.md`, `.rules`, or equivalent.
- Add a small skill such as `team-github-search`.
- Record exact commands that worked for that agent.
- State when to use the tool: before team-wide claims, repo discovery, issue
  archaeology, cross-repo duplicate checks, and onboarding to unfamiliar team
  repos.
- State when not to use it: as a replacement for memory, as proof without
  `team-gh show`, or for secrets/config discovery.

## Skill Template

Agents can adapt this as `.codex/skills/team-github-search/SKILL.md` or the
equivalent skill file for their substrate:

```md
---
name: team-github-search
description: Provides team-gh commands, workflow, and progressive disclosure pattern; use before team-wide claims, cross-repo duplicate checks, or onboarding to unfamiliar repos.
---

# Team GitHub Search

Use `team-gh` for source-backed GitHub discovery. It does not replace memory.

## When To Use

- Before claiming where a team decision lives.
- Before creating a duplicate issue or repo feature.
- When onboarding to an unfamiliar team repo.
- When searching issues, PRs, README files, AGENTS/CLAUDE docs, or markdown
  across all repos visible to this agent.

## Workflow

1. Start broad:

   ```bash
   team-gh search "<topic>" --scope all --limit 8 --refresh-repos
   ```

2. Narrow when likely repo or owner is known:

   ```bash
   team-gh search "<topic>" --repo example-org/example-repo --scope all --issue-search hybrid
   ```

3. Expand source before acting:

   ```bash
   team-gh show example-org/example-repo#123
   team-gh show example-org/example-repo README.md --lines 1:80
   ```

4. Cite the issue, PR, file, or URL that established the fact.

## When Not To Use

- Do not use search results as proof without expanding a source with
  `team-gh show`.
- Do not use this as a replacement for agent memory or local repo inspection.
- Do not use it to discover or expose secrets, private config, or credentials.

## Local Notes

Add this agent's tested commands here:

- `<command that worked>`
- `<command that worked>`
```

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
