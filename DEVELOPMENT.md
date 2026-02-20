# Development Standards

**This is the first file any developer or AI agent should read before making changes to OpenClaw Hub.**

It defines the rules for commits, releases, code style, documentation, and repository hygiene. Every change to this repository — whether by a human or an AI agent — must follow these standards.

---

## Table of Contents

- [Pre-Commit Checklist](#pre-commit-checklist)
- [Pre-Release Checklist](#pre-release-checklist)
- [Branch Management](#branch-management)
- [Commit Messages](#commit-messages)
- [Issue Linkage](#issue-linkage)
- [Code Style](#code-style)
- [Documentation Standards](#documentation-standards)
- [Testing Requirements](#testing-requirements)
- [File Ownership Map](#file-ownership-map)
- [Prohibited Patterns](#prohibited-patterns)

---

## Pre-Commit Checklist

Run through this checklist **before every commit to `main`** (or before marking a PR as ready):

### Always

- [ ] Code runs without errors: `uvicorn aigateway.main:app --host 127.0.0.1 --port 8080`
- [ ] Health check passes: `curl http://127.0.0.1:8080/health`
- [ ] No hardcoded credentials, API keys, or secrets anywhere in the diff
- [ ] No `print()` statements — use `structlog` for all logging
- [ ] Commit message follows [Conventional Commits](#commit-messages) format
- [ ] Commit references an issue number where applicable

### If you changed Python source code (`aigateway/`)

- [ ] All existing imports still resolve
- [ ] New functions and classes have docstrings
- [ ] Type hints on all new function signatures
- [ ] No new dependencies added without updating `requirements.txt`
- [ ] If you added a new API endpoint: verify it appears in Swagger UI at `/docs`

### If you changed API endpoints

- [ ] Swagger UI (`/docs`) loads and shows the new/modified endpoint
- [ ] Request and response schemas are documented with examples
- [ ] Existing endpoints still respond correctly (no regressions)

### If you changed the dashboard (`aigateway/static/` or dashboard HTML)

- [ ] Dashboard loads at `/dashboard` without console errors
- [ ] All four views render: Overview, Connections, Costs, Activity
- [ ] Theme and styling are consistent (dark theme, `#0a0e17` background, `#22d3ee` accent)

### If you changed install scripts (`scripts/`)

- [ ] Script is executable: `chmod +x scripts/<script>.sh`
- [ ] Shebang line is present: `#!/usr/bin/env bash`
- [ ] Script is idempotent — running it twice doesn't break anything

---

## Pre-Release Checklist

Run through this checklist **before tagging and publishing a new release**. This is separate from the pre-commit checklist — not every commit triggers a release.

### Version Bumps

Update the version string in **all** of the following locations:

| File | What to Update |
|------|---------------|
| `README.md` | Version in the Project Status section at the bottom |
| `README.md` | The release shield badge URL (if it's hardcoded rather than dynamic) |
| `CHANGELOG.md` | Add a new `## [x.y.z] - YYYY-MM-DD` entry at the top |
| `docs/STATUS.md` | Version and date |
| `aigateway/main.py` | Version string (if defined in code, e.g., in the FastAPI app metadata) |
| `aigateway/config.py` | Version constant (if one exists) |
| `.env.example` | Only if new environment variables were added since last release |

**How to find all version references:**

```bash
grep -rn "1\.2\.0" --include="*.py" --include="*.md" --include="*.yaml" --include="*.yml" .
```

Replace `1.2.0` with the current version to find everything that needs bumping.

### Changelog

The `CHANGELOG.md` entry must include:

- **Added** — new features, endpoints, capabilities
- **Changed** — modifications to existing behavior
- **Fixed** — bug fixes
- **Removed** — anything deprecated or deleted
- **Security** — vulnerability fixes (if any)

Only include categories that have entries. Don't add empty sections.

### Documentation

- [ ] `README.md` accurately describes the current state of the project
- [ ] Architecture tree in `README.md` matches the actual file structure
- [ ] All new features are documented (either in README or in `docs/`)
- [ ] No references to moved, renamed, or deleted files anywhere in the repo:
  ```bash
  # Check for broken internal links
  grep -rn "STATUS.md\|MVP-PLAN.md\|OPEN-SOURCE-CHECKLIST.md\|TEST-RESULTS.md\|SECURITY-AUDIT.md\|SECURITY-FIX-SUMMARY.md\|SECURITY-STATUS.md" --include="*.md" .
  ```

### Tagging and Publishing

```bash
git add -A
git commit -m "chore: Prepare vX.Y.Z release"
git tag vX.Y.Z
git push origin main --tags
```

Then create the GitHub release:
- Tag: `vX.Y.Z`
- Title: `vX.Y.Z — Short Description of Theme`
- Body: Expanded version of the CHANGELOG entry
- Check "Set as the latest release"

### Post-Release

- [ ] Verify the release appears on GitHub with "Latest" badge
- [ ] Verify the release shield badge in the README updated (may take a few minutes to cache)
- [ ] Delete the release branch if one was used

---

## Branch Management

### Naming Convention

All branches must use this format:

```
type/short-description
```

| Type | When to Use | Example |
|------|-------------|---------|
| `feature/` | New functionality | `feature/push-notifications` |
| `fix/` | Bug fixes | `fix/ollama-timeout-handling` |
| `refactor/` | Code restructuring | `refactor/extract-provider-base` |
| `docs/` | Documentation only | `docs/installation-guide` |
| `chore/` | Maintenance tasks | `chore/dependency-update` |

### Rules

- **Never commit directly to `main`** for features or fixes. Always use a branch + merge.
  - Exception: single-file documentation fixes and release prep commits can go directly to `main`.
- **Delete branches immediately after merging.** Do not accumulate stale branches.
- **Squash merge** is preferred for feature branches (produces a clean single commit on `main`).
- **Branch count target:** `main` + at most 2 active feature branches at any time. If there are more than 3 total branches, something needs to be merged or deleted.

### After Every Merge

```bash
# Delete the remote branch
git push origin --delete <branch-name>

# Delete the local branch
git branch -d <branch-name>

# Prune stale remote tracking references
git fetch --prune
```

---

## Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/).

### Format

```
type: short description (#issue-number)
```

### Types

| Type | When to Use |
|------|-------------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `docs` | Documentation only changes |
| `refactor` | Code restructuring with no behavior change |
| `test` | Adding or updating tests |
| `ci` | CI/CD workflow changes |
| `chore` | Maintenance (dependency updates, release prep, cleanup) |

### Rules

- Lowercase type and description
- No period at the end
- Imperative mood: "Add feature" not "Added feature" or "Adds feature"
- Keep the first line under 72 characters
- Reference the issue number in parentheses when applicable
- Multi-line body is optional but encouraged for complex changes

### Examples

```
feat: Add health probe monitoring for degraded connections (#29)

fix: Correct token count calculation for Anthropic streaming responses (#34)

docs: Update installation guide with Windows WSL2 instructions

refactor: Extract provider routing logic into separate module

chore: Prepare v1.3.0 release

ci: Add Python 3.13 to test matrix
```

### Bad Examples (Do Not Do This)

```
# No type prefix
Update README

# Past tense
feat: Added new dashboard endpoint

# Too vague
fix: Fixed stuff

# No issue reference for a feature
feat: Add push notifications
```

---

## Issue Linkage

- **Every `feat` and `fix` commit must reference a GitHub issue.** If no issue exists, create one first — even if it's a one-liner.
- **`docs`, `refactor`, `ci`, and `chore` commits** do not require an issue reference (but it's welcome).
- Use `(#NN)` at the end of the commit message first line.
- In the commit body or PR description, use `Closes #NN` or `Fixes #NN` to auto-close the issue on merge.

---

## Code Style

### Python

- **Python version:** 3.12+
- **Imports:** Standard library → third-party → local, separated by blank lines. Alphabetical within each group.
  ```python
  import os
  from pathlib import Path

  from fastapi import FastAPI
  from sqlalchemy import Column, Integer, String

  from aigateway.config import settings
  from aigateway.storage.database import get_db
  ```
- **Type hints:** Required on all function signatures (parameters and return types).
  ```python
  def get_provider(model: str) -> BaseProvider:
  ```
- **Docstrings:** Required on all public functions, classes, and modules. Use Google-style format.
  ```python
  def route_request(model: str, messages: list[dict]) -> dict:
      """Route a chat completion request to the appropriate provider.

      Args:
          model: The model identifier (e.g., "gpt-4o-mini", "claude-sonnet").
          messages: The conversation messages in OpenAI format.

      Returns:
          The provider's response in normalized format.

      Raises:
          ProviderNotFoundError: If no provider handles the given model.
      """
  ```
- **Logging:** Use `structlog` exclusively. Never use `print()`.
  ```python
  import structlog
  logger = structlog.get_logger()

  logger.info("request_routed", model=model, provider=provider.name, latency_ms=latency)
  ```
- **Constants:** Use UPPER_SNAKE_CASE. Define in `config.py` or at the top of the relevant module.
- **Line length:** 120 characters maximum.
- **String formatting:** f-strings preferred over `.format()` or `%`.

### SQL / Database

- All schema changes must be idempotent — safe to run on an existing database.
- New tables must be added to the migration logic in the database initialization.
- Column names use `snake_case`.
- Always include `created_at` and `updated_at` timestamps on new tables.

### Shell Scripts

- Shebang: `#!/usr/bin/env bash`
- Use `set -euo pipefail` at the top of every script.
- Scripts must be idempotent — running twice produces the same result as running once.
- All scripts live in `scripts/`. No shell scripts in the project root.

### HTML / Dashboard

- Dashboard UI is a single-file HTML response — no build tools, no npm, no separate frontend.
- Dark theme: `#0a0e17` background, `#1a1f2e` surface, `#22d3ee` accent.
- Fonts: DM Sans (body), JetBrains Mono (code/numbers).
- Charts: Chart.js.
- New dashboard features must work without page refresh (use fetch + DOM updates).

---

## Documentation Standards

### Inline Code Comments

- Comments explain **why**, not **what**. The code shows what; comments show intent.
- Do not leave commented-out code. Delete it — git has history.
- `TODO` comments must include an issue number: `# TODO(#42): Add retry logic for rate limits`
- `FIXME` is prohibited. If something is broken, fix it or file an issue.

### Markdown Files

- Use ATX-style headers (`#`, `##`, `###`).
- One sentence per line (makes diffs cleaner).
- Code blocks must specify the language: ` ```python `, ` ```bash `, ` ```yaml `.
- Internal links use relative paths: `[CONTRIBUTING](CONTRIBUTING.md)`, not full GitHub URLs.
- No trailing whitespace.

### README Updates

The README must always reflect the **current released state** of the project. Specifically:

- The feature list must only include features that are implemented and working.
- The architecture tree must match the actual directory structure.
- The version in the Project Status section must match the latest release tag.
- Installation instructions must work on a clean machine.

If a feature is in progress but not merged, it does not go in the README.

---

## Testing Requirements

### Before Any Commit to Main

At minimum, verify:

```bash
# Server starts
uvicorn aigateway.main:app --host 127.0.0.1 --port 8080 &

# Health check
curl -s http://127.0.0.1:8080/health | python3 -m json.tool

# Swagger loads
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/docs
# Expected: 200

# Dashboard loads
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/dashboard
# Expected: 200

# Kill the server
kill %1
```

### Before a Release

Run the full test suite:

```bash
# Run unit tests
python -m pytest tests/ -v

# Run the manual endpoint sweep (if automated tests don't cover it)
# Verify all endpoints listed in Swagger return expected status codes
```

### For New Features

- New API endpoints must have at least one test in `tests/`.
- New provider implementations must have a test covering the happy path and at least one error case.

---

## File Ownership Map

Understanding which files are hand-maintained vs. auto-generated prevents accidental overwrites.

### Hand-Maintained (edit directly)

| File/Directory | Owner | Notes |
|---------------|-------|-------|
| `aigateway/` | Developer | All Python source code |
| `scripts/` | Developer | Install and utility scripts |
| `tests/` | Developer | Test files |
| `docs/` | Developer | All documentation |
| `examples/` | Developer | Workflow YAML examples |
| `README.md` | Developer | Must match current release state |
| `CHANGELOG.md` | Developer | Updated only at release time |
| `CONTRIBUTING.md` | Developer | Rarely changes |
| `DEVELOPMENT.md` | Developer | This file — update when standards evolve |
| `SECURITY.md` | Developer | Rarely changes |
| `CODE_OF_CONDUCT.md` | Developer | Rarely changes |
| `.env.example` | Developer | Update when new env vars are added |
| `requirements.txt` | Developer | Update when dependencies change |
| `.gitignore` | Developer | Update as needed |

### Auto-Generated (do not edit manually)

| File/Directory | Generated By | Notes |
|---------------|-------------|-------|
| `aigateway.db` | SQLite / SQLAlchemy | Runtime database — never commit |
| `.env` | User / installer | Contains secrets — never commit |
| `venv/` | Python | Virtual environment — never commit |
| `__pycache__/` | Python | Bytecode cache — never commit |
| `.github/workflows/*.yml` | Developer initially | But CI runs are auto-generated |

### Files That Must Stay in Root

These files must remain in the project root — GitHub and tooling expect them here:

- `README.md`
- `LICENSE`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `SECURITY.md`
- `DEVELOPMENT.md`
- `.env.example`
- `.gitignore`
- `requirements.txt`

Everything else belongs in a subdirectory.

---

## Prohibited Patterns

The following patterns must **never** appear in committed code:

| Pattern | Why | What to Do Instead |
|---------|-----|-------------------|
| `print()` | Not structured, not filterable | Use `structlog.get_logger()` |
| Hardcoded API keys or secrets | Security risk | Use `.env` and `config.py` |
| `TODO` without issue number | Creates invisible tech debt | Write `# TODO(#NN):` or file an issue |
| `FIXME` | Implies known-broken code was committed | Fix it or file an issue and reference it |
| Commented-out code | Clutters the codebase | Delete it — git has history |
| `import *` | Makes dependencies invisible | Use explicit imports |
| Bare `except:` | Swallows all errors including system exits | Use `except Exception:` at minimum |
| `time.sleep()` in async code | Blocks the event loop | Use `asyncio.sleep()` |
| Files in project root that aren't in the [root allowlist](#files-that-must-stay-in-root) | Clutters the root directory | Move to appropriate subdirectory |
| Branches that have been merged | Clutters the branch list | Delete immediately after merge |

---

## Quick Reference Card

Copy this into your commit workflow as a fast checklist:

```
PRE-COMMIT:
□ Server starts and /health returns 200
□ No print(), no hardcoded secrets, no bare except
□ Conventional Commit message with issue reference
□ New functions have docstrings and type hints
□ requirements.txt updated if deps changed

PRE-RELEASE:
□ Version bumped in: README.md, CHANGELOG.md, STATUS.md, source code
□ CHANGELOG has Added/Changed/Fixed/Removed sections
□ Architecture tree in README matches reality
□ grep for old version string returns zero results
□ All tests pass
□ Tag, push, create GitHub release with "Latest" checked
□ Delete release branch

POST-MERGE:
□ Delete the remote branch
□ Delete the local branch
□ git fetch --prune
```
