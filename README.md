# SEC Financial Data MCP Pro

**$19/month** — XBRL financial data, SEC filings, and GAAP metrics via MCP.
▶ [Subscribe Now](https://buy.stripe.com/4gM6oJa1xck44vCenp1oI0p)

An MCP (Model Context Protocol) server that provides tools to access **SEC EDGAR** financial data — including XBRL company facts, filing histories, and GAAP financial metrics.

## Tools

| Tool | Description |
|------|-------------|
| `get_company_facts` | Fetch all XBRL financial facts reported by a company (by CIK) |
| `search_filings` | List recent SEC filings by ticker/CIK, optionally filtered by form type |
| `get_submissions` | Get a company's full submission history |
| `get_financial_metric` | Retrieve a single GAAP metric for a specific company and fiscal year |

## Usage

### With MCP-compatible clients (Claude Desktop, VS Code Copilot, etc.)

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "sec-financial": {
      "command": "python",
      "args": ["/path/to/sec-financial-mcp/server.py"]
    }
  }
}
```

### Run directly (stdio)

```bash
python server.py
```

The server communicates over **stdio** using the MCP protocol.

### Example queries

Once connected, your AI assistant can ask:

- "Get company facts for Apple (CIK: 320193)"
- "Search recent 10-K filings for Microsoft"
- "What were Tesla's total assets in 2023?"
- "Get submission history for Amazon"

## API Endpoints

The server wraps the following **SEC EDGAR** public endpoints:

| Endpoint | Description |
|----------|-------------|
| `GET /api/xbrl/companyfacts/CIK{10-digit-CIK}.json` | XBRL company facts |
| `GET /submissions/CIK{10-digit-CIK}.json` | Filing submission history |
| `GET /cgi-bin/browse-edgar` | Filing search (Atom XML) |

## Configuration

- **User-Agent**: `AgentPay MCP (jackpost1388@wshu.net)` (required by SEC)
- **Rate limit**: 10 req/s; recommended 1 req/s
- No API key or authentication required

## GAAP Tags (Common)

- `Assets`
- `Liabilities`
- `RevenueFromContractWithCustomerExcludingAssessedTax`
- `NetIncomeLoss`
- `EarningsPerShareBasic`
- `OperatingIncomeLoss`
- `CashAndCashEquivalentsAtCarryingValue`
- `StockholdersEquity`

Browse the full [SEC XBRL Taxonomy](https://www.sec.gov/info/edgar/edgartaxonomies.shtml) for more tags.

## Deployment

This server can be deployed on [Smithery](https://smithery.ai). See `smithery.yaml` for configuration.

## License

MIT
