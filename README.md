# School Finance MCP

[![CI](https://github.com/tylermbeau-jpg/school-finance-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/tylermbeau-jpg/school-finance-mcp/actions/workflows/ci.yml)

A Model Context Protocol (MCP) server that gives an LLM agent first-class tools for California school finance:

- Validate and decode **SACS account strings** (the state's 19-digit Standardized Account Code Structure).
- Compute **school-meal reimbursement** for the National School Lunch and Breakfast Programs, including the California Universal Meals state top-up.

It is a small, self-contained server built with the official MCP Python SDK (FastMCP). The point is to take a gnarly, real-world domain (California K-12 fund accounting and child-nutrition reimbursement) and expose it as clean, agent-callable tools with typed inputs and structured output.

**[Try the live demo](https://tylermbeau-jpg.github.io/school-finance-mcp/)**: check an account string in your browser against the hosted server. The page calls the real `/mcp` endpoint and shows the result, the checks applied, and the response time.

The hosted instance answers in well under a second. It runs on a free host that sleeps when idle, so the demo page wakes it and shows when it is ready (a wake takes up to a minute). If the host is asleep when a client connects, the first request waits for that wake, so open the demo page first. To connect Claude Code to the same instance:

```bash
claude mcp add --transport http school-finance https://school-finance-mcp.onrender.com/mcp
```

## Tools

| Tool | What it does |
|---|---|
| `validate_sacs_string` | Validate a SACS account string against CDE's rules. Accepts delimited (`01-0000-0-1110-1000-1100`) or packed 19-digit form. Checks structure, then CDE's valid-code lists and all seven valid-combination matrices, reported under the technical review's own check ids with CDE's severity. Optional `fiscal_year` ("2025-26"); default is the latest tables on file. |
| `decode_sacs_string` | Decode a SACS string into its six components (fund, resource, project year, goal, function, object), each with its code and a human-readable description, plus the resource restriction band. |
| `list_sacs_codes` | CDE's full valid-code list for `fund`, `resource`, `goal`, `function`, or `object` (optional `fiscal_year`), plus descriptive reference: series, ranges, common names. `project_year` returns its definition. |
| `calculate_meal_reimbursement` | Compute federal (and optional California Universal Meals) reimbursement from counts of lunches and breakfasts by category, with tier flags for high-ISP lunch, severe-need breakfast, performance-based certification, and the CA state top-up. Returns an itemized breakdown. |

## The SACS account string

The CDE state account string is 19 digits across six fields:

| Field | Digits | Meaning |
|---|---|---|
| Fund | 2 | The accounting entity (for example General Fund, Cafeteria Fund). |
| Resource | 4 | Funding source and its restrictions (restricted vs unrestricted). |
| Project Year | 1 | Grant or project year for multi-year resources (0 if not applicable). |
| Goal | 4 | The student population or instructional setting served. |
| Function | 4 | The activity performed (Instruction, Food Services, Plant Maintenance, etc.). |
| Object | 4 | The type of revenue, expenditure, or balance-sheet item. |

Example: `01-0000-0-1110-1000-1100` is General Fund, unrestricted, no project year, General Education K-12, Instruction, certificated teacher salaries.

## Valid combinations

CDE publishes, each fiscal year, the valid codes for every SACS dimension and seven matrices of which codes may be combined. The SACS Web System's technical review applies them under check ids like `CHK-FUNDxRESOURCE`; a failing check is what stops an official export. `validate_sacs_string` applies the same tables to one string and reports under the same ids, so its output compares line for line with the TRC screen:

```
validate_sacs_string("21-5310-0-0000-3700-4700")
-> valid: false, tables: "2026-27"
   combination_errors: CHK-FUNDxRESOURCE (W): Fund 21 is not valid with Resource 5310 ...
```

Scoping follows CDE: Goal x Function applies only to expenditure objects and to functions 1000-1999, 4000-5999 and 7200-7999 (except 7210); Resource x Object splits into A (objects 8000-9999) and B (1000-7999) and skips the beginning-balance objects 9791/9793/9795; Fund x Function is fatal (B) for funds 01, 09 and 62 and a warning (A) elsewhere. A code missing from CDE's list fails its CHECK<DIM> once and the combinations involving it are listed as not evaluated. Pairs a matrix does not cover are listed as not covered rather than claimed either way.

This is the check, not the fix: the server proposes no replacement codes, checks no balances or transfers, and reads no export files. The tables live in `school_finance_mcp/data/combos_<year>.json`, generated from CDE's valid-combination spreadsheets (a cell counts as valid when CDE marks it valid for school districts). A new fiscal year means regenerating the file from CDE's release and citing it in the commit.

## Install

Requires Python 3.10 or newer.

```bash
git clone https://github.com/tylermbeau-jpg/school-finance-mcp.git
cd school-finance-mcp
python3.12 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e ".[dev]"
```

## Run

```bash
.venv/bin/python -m school_finance_mcp
```

The server speaks MCP over stdio by default, so it waits for an MCP client to connect (it will not print anything on its own). Connect it to Claude Desktop or Claude Code below, or test it with any MCP client.

## Run as a remote server (streamable HTTP)

The same server can serve MCP over streamable HTTP, at the `/mcp` path:

```bash
.venv/bin/python -m school_finance_mcp --transport http
```

That listens on `http://127.0.0.1:8000/mcp` (`--host` and `--port` to change it; `$PORT` is respected for cloud platforms). Connect Claude Code to it:

```bash
claude mcp add --transport http school-finance http://127.0.0.1:8000/mcp
```

The HTTP mode is stateless (every tool is a pure function), so it works behind restarts and load balancers with no session store.

Two more things come with http mode:

- `GET /health` returns `{"status": "ok"}` and is readable from any origin, so a status page or uptime check can tell a host that is still waking from a server that is up.
- `--cors-origin https://your-site.example` (repeatable) lets a page on that origin call `/mcp` straight from the browser. Without it, browser calls from other origins are refused.

The [live demo](https://tylermbeau-jpg.github.io/school-finance-mcp/) is a single static page in `docs/` that uses both. Add `?endpoint=https://your-server` to its URL to point it at another deployment.

### Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/tylermbeau-jpg/school-finance-mcp)

The repo ships a `render.yaml` blueprint: a free-tier Python web service running `python -m school_finance_mcp --transport http --host 0.0.0.0`, plus a `--cors-origin` for this repo's demo page (change or drop it in your own fork). After deploying, your endpoint is `https://<your-service>.onrender.com/mcp` (the reference instance above runs from exactly this blueprint). Render's hostname is allowed through DNS rebinding protection automatically via `$RENDER_EXTERNAL_HOSTNAME`; on other platforms, pass your public hostname with `--allowed-host`. Free-tier services sleep when idle, so the first request after a quiet period waits for the host to wake (up to a minute); after that, responses return in well under a second.

## Test

```bash
.venv/bin/python -m pytest -q
```

## Connect to Claude Desktop

Add this to your Claude Desktop config (on macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`), using absolute paths, then restart Claude Desktop:

```json
{
  "mcpServers": {
    "school-finance": {
      "command": "/absolute/path/to/school-finance-mcp/.venv/bin/python",
      "args": ["-m", "school_finance_mcp"]
    }
  }
}
```

## Connect to Claude Code

```bash
claude mcp add school-finance -- /absolute/path/to/school-finance-mcp/.venv/bin/python -m school_finance_mcp
```

Then ask the agent things like "decode SACS string 13-5310-0-0000-3700-4700" or "what is the federal reimbursement for 500 free and 200 paid lunches with the California top-up?".

## Data sources

Reference data is built from public sources and is current for school year 2025-26.

- CDE SACS account-code structure and valid codes: https://www.cde.ca.gov/fg/ac/ac/
- CDE SACS Import File Specifications (field widths): https://www.cde.ca.gov/fg/ac/ac/importspecs.asp
- CDE Valid Codes and Combinations: https://www.cde.ca.gov/fg/ac/ac/validcodes.asp
- CDE valid-combination spreadsheets (source of `data/combos_<year>.json`): https://www.cde.ca.gov/fg/ac/ac/sprvalidcombs.asp
- USDA FNS National Average Payment rates, SY 2025-26: https://www.fns.usda.gov/schoolmeals/fr-072425
- CDE California Universal Meals: https://www.cde.ca.gov/ls/nu/sn/cauniversalmeals.asp

## Disclaimer

This server is illustrative. SACS validation here covers structure, CDE's valid codes, and CDE's valid combinations for school districts (the D flag in CDE's matrices) for one string at a time; it does not check balances, transfers, or whole export files, and it proposes no corrections. Meal rates are the published SY 2025-26 figures and the California reimbursement model is simplified. For official work, run the SACS Web System's technical review on the full export and confirm current rates and apportionment rules with USDA FNS and the CDE.

## License

MIT. See LICENSE.
