"""School Finance MCP: California SACS validation and school-meal reimbursement tools.

A Model Context Protocol server that gives an LLM agent first-class tools for
California school finance: validating and decoding SACS (Standardized Account
Code Structure) account strings, and computing National School Lunch / Breakfast
Program reimbursement including the California Universal Meals state top-up.

Built from public CDE and USDA FNS reference material. It is illustrative: the
authoritative valid-combination tables and current rates are published by the
CDE and USDA and should be used for official work.
"""

__version__ = "0.1.0"
