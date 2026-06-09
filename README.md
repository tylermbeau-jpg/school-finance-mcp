# School Finance MCP

A Model Context Protocol (MCP) server that gives an LLM agent first-class tools for California school finance:

- Validate and decode **SACS account strings** (the state's 19-digit Standardized Account Code Structure).
- Compute **school-meal reimbursement** for the National School Lunch and Breakfast Programs, including the California Universal Meals state top-up.

It is a small, self-contained server built with the official MCP Python SDK (FastMCP). The point is to take a gnarly, real-world domain (California K-12 fund accounting and child-nutrition reimbursement) and expose it as clean, agent-callable tools with typed inputs and structured output.

## Tools

| Tool | What it does |
|---|---|
| `validate_sacs_string` | Validate a SACS account string. Accepts delimited (`01-0000-0-1110-1000-1100`) or packed 19-digit form. Checks field widths, numeric content, and known codes. Returns `valid`, structural `errors`, `warnings`, parsed `components`, and a `normalized` form. |
| `decode_sacs_string` | Decode a SACS string into its six components (fund, resource, project year, goal, function, object), each with its code and a human-readable description, plus the resource restriction band. |
| `list_sacs_codes` | List the known codes or ranges for a field: `fund`, `resource`, `project_year`, `goal`, `function`, or `object`. |
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

## Install

Requires Python 3.10 or newer.

```bash
git clone <your-repo-url> school-finance-mcp
cd school-finance-mcp
python3.12 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e ".[dev]"
```

## Run

```bash
.venv/bin/python -m school_finance_mcp
```

The server speaks MCP over stdio, so it waits for an MCP client to connect (it will not print anything on its own). Connect it to Claude Desktop or Claude Code below, or test it with any MCP client.

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
- USDA FNS National Average Payment rates, SY 2025-26: https://www.fns.usda.gov/schoolmeals/fr-072425
- CDE California Universal Meals: https://www.cde.ca.gov/ls/nu/sn/cauniversalmeals.asp

## Disclaimer

This server is illustrative. SACS validation here is structural plus known-code lookup; it does not perform the full valid-combination check the CDE enforces (which Resource, Goal, Function, and Object codes are allowed together, by entity type). Meal rates are the published SY 2025-26 figures and the California reimbursement model is simplified. For official work, validate against the CDE's downloadable valid-code and valid-combination tables and confirm current rates and apportionment rules with USDA FNS and the CDE.

## License

MIT. See LICENSE.
