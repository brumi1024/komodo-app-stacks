---
name: renovate-pr-triage
description: Triage Renovate dependency pull requests for homelab application stacks. Use when reviewing a Renovate PR, dependency dashboard item, Docker image update, grouped dependency bump, or upgrade risk before merge.
---

# Renovate PR Triage

Produce a read-only, evidence-backed risk matrix.
Leave edits, comments, approvals, closes, and merges to an explicit follow-up request.

## Establish the change

1. Resolve the PR number or URL and confirm the author is Renovate.
2. Read the repository `AGENTS.md`, `renovate.json`, PR body, changed files, diff, commits, and status checks.
3. Split grouped PRs into one row per dependency or image.
4. Find every runtime and configuration reference with `rg`; distinguish a live dependency from an unused or stale declaration.
5. Follow release links from the PR and inspect primary upstream release notes, migration guides, image documentation, and known compatibility constraints.
6. Run `python3 scripts/validate_stacks.py` when the checkout contains the proposed change.

Use `gh pr view` and `gh pr diff` for GitHub state.
Treat passing checks as necessary evidence, not proof that a stateful deployment is safe.

## Classify each update

- `SAFE`: no breaking, schema, data, configuration, or deployment migration is indicated; repository validation passes; the dependency is live and the update has a clear rollback.
- `DEAD`: the dependency is no longer consumed by the deployed shape. Recommend removing the stale reference separately instead of merging a meaningless bump.
- `VERIFY`: evidence is incomplete or the update needs bounded runtime verification that CI cannot provide.
- `MIGRATE`: the update changes configuration, APIs, storage layout, database schema, persistent data, authentication, networking, or deployment procedure.

Classify database majors, Forgejo majors, and any update that changes a persistent-data format as `MIGRATE`.
Respect explicit constraints in `renovate.json`, including disabled Immich database updates and grouped Caddy builds.
For a grouped PR, the overall verdict is the highest-risk row.

## Report

Return:

| Dependency | Update | Verdict | Evidence | Required action |
| --- | --- | --- | --- | --- |

Then state:

- Overall verdict.
- Validation and checks observed.
- Evidence gaps.
- Smallest safe next step and rollback boundary.

Link every upstream claim to its primary source.
Do not copy a Merge Confidence badge into the verdict without explaining the repository-specific evidence behind it.
