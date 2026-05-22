"""
SEC Financial Data MCP Server

Provides tools to access SEC EDGAR financial data including XBRL filings,
company facts, submission history, and financial metrics.

Uses the public SEC EDGAR API with required User-Agent header.
Rate limit: 10 requests/second (recommended: 1 request/second).

Usage:
  python3 server.py                    # Free tier (50 calls/instance)
  python3 server.py --pro-key PROL_XXX  # Pro tier (unlimited)
"""

from typing import Any
import httpx
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from mcp.types import Tool, TextContent, CallToolResult

# ── Constants ──────────────────────────────────────────────────────────────

USER_AGENT = "AgentPay MCP (jackpost1388@wshu.net)"
BASE_URL = "https://data.sec.gov"
SEARCH_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
HEADERS = {"User-Agent": USER_AGENT}

# ── Rate Limiting & Pro Key ────────────────────────────────────────────────

FREE_LIMIT = 50
PRO_KEYS = {"PROL_AGENTPAY_DEMO": "demo"}  # Demo key for testing

# Parse --pro-key from command line
import sys
PRO_KEY = None
for i, arg in enumerate(sys.argv):
    if arg == "--pro-key" and i + 1 < len(sys.argv):
        PRO_KEY = sys.argv[i + 1]
        break

IS_PRO = PRO_KEY in PRO_KEYS
call_counter = 0

STRIPE_LINK = "https://buy.stripe.com/4gM6oJa1xck44vCenp1oI0p"  # $19/mo (SEC EDGAR MCP Pro)

def check_rate_limit():
    """Check if free tier has exceeded limit. Returns error dict or None."""
    global call_counter
    if IS_PRO:
        return None
    call_counter += 1
    if call_counter > FREE_LIMIT:
        remaining = call_counter - FREE_LIMIT
        return {
            "error": f"Free tier limit reached ({FREE_LIMIT} calls). Upgrade to Pro for unlimited access.",
            "isError": True,
            "next_steps": [
                f"Purchase Pro at {STRIPE_LINK} ($19/mo, unlimited)",
                "Restart the server to reset the free counter",
                "Use --pro-key PROL_XXX to run in Pro mode"
            ],
            "calls_used": call_counter,
            "limit": FREE_LIMIT,
            "over_by": remaining
        }
    return None


# ── Server Setup ──────────────────────────────────────────────────────────

server = Server("sec-financial-mcp")


# ── Helper Functions ───────────────────────────────────────────────────────

def _cik_padded(cik: str | int) -> str:
    """Zero-pad a CIK number to 10 digits as required by the SEC API.

    Accepts strings with or without leading zeros, or an integer.
    Returns a 10-digit zero-padded string.
    """
    cik_str = str(cik).strip().lstrip("0")
    if cik_str == "":
        cik_str = "0"
    return cik_str.zfill(10)


async def _sec_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Make an authenticated GET request to the SEC EDGAR API.

    Args:
        path: URL path relative to data.sec.gov
        params: Optional query parameters

    Returns:
        Parsed JSON response as a dictionary

    Raises:
        RuntimeError: On HTTP errors or connection issues
    """
    url = f"{BASE_URL}{path}"
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
        resp = await client.get(url, params=params)
        if resp.status_code == 404:
            raise RuntimeError(
                f"Resource not found at {url}. Check that the CIK is valid."
            )
        if resp.status_code == 429:
            raise RuntimeError(
                "Rate limited by SEC EDGAR. Please wait and try again."
            )
        resp.raise_for_status()
        return resp.json()


# ── MCP Tool Definitions ──────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_company_facts",
            description=(
                "Get XBRL financial data for a company identified by its "
                "Central Index Key (CIK). Returns all company facts reported "
                "to the SEC in XBRL format across all filings."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "cik": {
                        "type": "string",
                        "description": (
                            "CIK number of the company (with or without "
                            "leading zeros, e.g. '320193' or '0000320193')"
                        ),
                    }
                },
                "required": ["cik"],
            },
        ),
        Tool(
            name="search_filings",
            description=(
                "Search SEC filings for a company by ticker symbol or CIK. "
                "Returns a list of recent filings matching the given form type."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker_or_cik": {
                        "type": "string",
                        "description": (
                            "Stock ticker symbol (e.g. 'AAPL') or CIK number"
                        ),
                    },
                    "form_type": {
                        "type": "string",
                        "description": (
                            "SEC form type to filter by (e.g. '10-K', '10-Q', "
                            "'8-K', '4'). Use empty string for all forms."
                        ),
                        "default": "",
                    },
                    "count": {
                        "type": "integer",
                        "description": (
                            "Number of recent filings to return (max 100)"
                        ),
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
                "required": ["ticker_or_cik"],
            },
        ),
        Tool(
            name="get_submissions",
            description=(
                "Get submission history for a company by CIK. Returns metadata "
                "about the company and a list of all recent SEC filings."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "cik": {
                        "type": "string",
                        "description": (
                            "CIK number of the company (e.g. '320193' or "
                            "'0000320193')"
                        ),
                    }
                },
                "required": ["cik"],
            },
        ),
        Tool(
            name="get_financial_metric",
            description=(
                "Get a specific GAAP financial metric for a company by CIK "
                "for a given year. Returns the reported value, unit, and "
                "filing context. Common GAAP tags include: "
                "Assets, Liabilities, RevenueFromContractWithCustomerExcludingAssessedTax, "
                "NetIncomeLoss, EarningsPerShareBasic, "
                "OperatingIncomeLoss, CashAndCashEquivalentsAtCarryingValue, "
                "StockholdersEquity."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "cik": {
                        "type": "string",
                        "description": (
                            "CIK number of the company (e.g. '320193' or "
                            "'0000320193')"
                        ),
                    },
                    "gaap_tag": {
                        "type": "string",
                        "description": (
                            "GAAP taxonomy tag name (e.g. 'Assets', "
                            "'NetIncomeLoss', 'RevenueFromContractWithCustomerExcludingAssessedTax')"
                        ),
                    },
                    "year": {
                        "type": "integer",
                        "description": (
                            "Fiscal year to retrieve the metric for "
                            "(e.g. 2023, 2024)"
                        ),
                    },
                },
                "required": ["cik", "gaap_tag", "year"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(
    name: str, arguments: dict[str, Any]
) -> CallToolResult:
    # Rate limit check
    limit_check = check_rate_limit()
    if limit_check:
        return TextContent(type="text", text=str(limit_check))
    try:
        match name:
            case "get_company_facts":
                cik = _cik_padded(arguments["cik"])
                data = await _sec_get(f"/api/xbrl/companyfacts/CIK{cik}.json")
                return TextContent(type="text", text=str(data))

            case "search_filings":
                ticker_or_cik = arguments["ticker_or_cik"]
                form_type = arguments.get("form_type", "")
                count = arguments.get("count", 10)

                params: dict[str, Any] = {
                    "action": "getcompany",
                    "owner": "exclude",
                    "output": "atom",
                }

                # Accept either a raw CIK or a ticker
                if ticker_or_cik.isdigit():
                    params["CIK"] = ticker_or_cik
                else:
                    params["CIK"] = ticker_or_cik

                if form_type:
                    params["type"] = form_type

                params["count"] = str(count)

                async with httpx.AsyncClient(
                    headers=HEADERS, follow_redirects=True
                ) as client:
                    resp = await client.get(SEARCH_URL, params=params)
                    if resp.status_code == 429:
                        raise RuntimeError(
                            "Rate limited by SEC EDGAR. Please wait and try again."
                        )
                    resp.raise_for_status()

                # Return the XML response as text (the browse-edgar endpoint returns Atom XML)
                return TextContent(
                    type="text",
                    text=resp.text,
                )

            case "get_submissions":
                cik = _cik_padded(arguments["cik"])
                data = await _sec_get(f"/submissions/CIK{cik}.json")
                return TextContent(type="text", text=str(data))

            case "get_financial_metric":
                cik = _cik_padded(arguments["cik"])
                gaap_tag = arguments["gaap_tag"]
                year = arguments["year"]

                facts = await _sec_get(
                    f"/api/xbrl/companyfacts/CIK{cik}.json"
                )

                # Navigate to the requested GAAP tag
                us_gaap = facts.get("facts", {}).get("us-gaap", {})
                tag_data = us_gaap.get(gaap_tag)
                if tag_data is None:
                    # Check if they might be in an extended taxonomy
                    for taxonomy, labels in facts.get("facts", {}).items():
                        if gaap_tag in labels:
                            tag_data = labels[gaap_tag]
                            break

                if tag_data is None:
                    available_tags = list(us_gaap.keys())
                    raise RuntimeError(
                        f"GAAP tag '{gaap_tag}' not found for CIK {cik}. "
                        f"Available tags include: {', '.join(available_tags[:20])}"
                    )

                # Find the matching year in the units
                units = tag_data.get("units", {})
                result_entries = []

                for unit, entries in units.items():
                    for entry in entries:
                        end = entry.get("end")
                        if end and str(year) in end:
                            result_entries.append(
                                {
                                    "value": entry.get("val"),
                                    "unit": unit,
                                    "end": end,
                                    "filed": entry.get("filed"),
                                    "frame": entry.get("frame"),
                                    "fy": entry.get("fy"),
                                    "fp": entry.get("fp"),
                                    "form": entry.get("form"),
                                }
                            )

                if not result_entries:
                    raise RuntimeError(
                        f"No data found for '{gaap_tag}' in {year} for CIK {cik}."
                    )

                return TextContent(type="text", text=str(result_entries))

            case _:
                raise ValueError(f"Unknown tool: {name}")

    except RuntimeError as e:
        return TextContent(type="text", text=f"Error: {e}")
    except Exception as e:
        return TextContent(
            type="text",
            text=f"Unexpected error: {type(e).__name__}: {e}",
        )


# ── Entry Point ────────────────────────────────────────────────────────────

async def main() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="sec-financial-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
