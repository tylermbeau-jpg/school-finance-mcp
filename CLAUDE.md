# school-finance-mcp

MCP server for California school finance, built from public CDE/USDA data only. Tools: `validate_sacs_string` (structure + CDE valid codes + CDE valid combinations), `decode_sacs_string`, `list_sacs_codes`, `calculate_meal_reimbursement`. MIT licensed.

**This repo is PUBLIC** (github.com/tylermbeau-jpg/school-finance-mcp, portfolio piece). Nothing non-public goes in it: no district data, no client or employer references, no internal file paths. Public data sources only.

## Commands

- Setup: `python3.12 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"` (needs Python 3.10+)
- Run: `.venv/bin/python -m school_finance_mcp` (MCP over stdio, the default) or `--transport http` for streamable HTTP at /mcp plus a `/health` probe (`--host`/`--port`, $PORT respected; `--cors-origin` lets a browser page on that origin call /mcp, and on Render the repo owner's GitHub Pages origin is allowed automatically from $RENDER_GIT_REPO_SLUG; render.yaml deploys this mode)
- Tests: `.venv/bin/python -m pytest -q` (SACS + CNP suites plus end-to-end http-mode tests; keep them passing)
- Demo page: `docs/index.html`, served by GitHub Pages at tylermbeau-jpg.github.io/school-finance-mcp. Static, no build step. It wakes the hosted instance through `/health`, then calls `/mcp` from the browser. To test it locally, serve `docs/` on a port, run the server with `--cors-origin http://127.0.0.1:<that port>`, and open the page with `?endpoint=http://127.0.0.1:8000`.

## Design boundaries

- SACS validation is structure + CDE valid codes + CDE valid combinations (the seven matrices in `data/combos_<year>.json`, reported under TRC check ids; see `combos.py`). Deliberately OUT of scope for this public repo: proposing replacement codes (nearest-code corrections), balance and transfer checks, whole-file runs, TRC log tie-out. Do not add those here.
- New fiscal year: regenerate `data/combos_<year>.json` from CDE's valid-combination spreadsheets (https://www.cde.ca.gov/fg/ac/ac/sprvalidcombs.asp) and cite the release in the commit. The year N file covers fiscal year N to N+1.
- Meal rates in `cnp.py` are an SY 2025-26 snapshot with no auto-fetch. New school year means a manual rate update with the USDA/CDE source cited in the commit.
- Connects to Claude Desktop via `claude_desktop_config.json` or `claude mcp add`; keep README instructions accurate for both.

## Gotchas

- `.venv/` has ended up tracked in the past; keep it out of commits (it bloats a public repo).
- To make the repo private if ever needed: `gh repo edit tylermbeau-jpg/school-finance-mcp --visibility private`.

## Working standards

- No em dashes or en dashes in anything: docs, code comments, commit messages. Use a period, comma, parentheses, or colon.
- Never announce work as done with unflagged incomplete parts. If anything is unfinished, uncertain, or untested, lead with that.
- Verify before declaring ready: run the tests, run the server, check the README still matches.
