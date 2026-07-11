# school-finance-mcp

MCP server for California school finance, built from public CDE/USDA data only. Tools: `validate_sacs_string`, `decode_sacs_string`, `list_sacs_codes`, `calculate_meal_reimbursement`. MIT licensed.

**This repo is PUBLIC** (github.com/tylermbeau-jpg/school-finance-mcp, portfolio piece). Nothing non-public goes in it: no district data, no client or employer references, no internal file paths. Public data sources only.

## Commands

- Setup: `python3.12 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"` (needs Python 3.10+)
- Run: `.venv/bin/python -m school_finance_mcp` (MCP over stdio; no HTTP server)
- Tests: `.venv/bin/python -m pytest -q` (SACS + CNP suites; keep them passing)

## Design boundaries

- SACS validation is structural plus known-code checks. It does NOT validate which Resource/Goal/Function/Object combinations are allowed together (that needs CDE combination tables, deliberately deferred). Don't claim combination validation in docs or tool descriptions.
- Meal rates in `cnp.py` are an SY 2025-26 snapshot with no auto-fetch. New school year means a manual rate update with the USDA/CDE source cited in the commit.
- Connects to Claude Desktop via `claude_desktop_config.json` or `claude mcp add`; keep README instructions accurate for both.

## Gotchas

- `.venv/` has ended up tracked in the past; keep it out of commits (it bloats a public repo).
- To make the repo private if ever needed: `gh repo edit tylermbeau-jpg/school-finance-mcp --visibility private`.

## Working standards

- No em dashes or en dashes in anything: docs, code comments, commit messages. Use a period, comma, parentheses, or colon.
- Never announce work as done with unflagged incomplete parts. If anything is unfinished, uncertain, or untested, lead with that.
- Verify before declaring ready: run the tests, run the server, check the README still matches.
