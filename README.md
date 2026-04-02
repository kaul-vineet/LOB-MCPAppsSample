# The Great Trading Company — LOB MCP Apps

| | |
|---|---|
| **Subtitle** | A multi-LOB MCP Apps platform for M365 Copilot — Salesforce CRM and ServiceNow ITSM in one agent |
| **Author** | Vineet Kaul, PM Architect – Agentic AI, Microsoft |
| **Date** | April 2026 |
| **Stack** | Python · FastMCP 1.26 · Salesforce REST API · ServiceNow Table API · Microsoft Dev Tunnels · M365 Agents Toolkit |

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![MCP SDK](https://img.shields.io/badge/FastMCP-1.26-green)
![M365](https://img.shields.io/badge/M365_Copilot-Public_Preview-orange)
![Salesforce](https://img.shields.io/badge/Salesforce-v62.0-00A1E0)
![ServiceNow](https://img.shields.io/badge/ServiceNow-Table_API-293E40)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

**Tags:** `mcp` `copilot` `python` `m365` `salesforce` `servicenow` `agentic-ai` `declarative-agent` `mcp-apps` `crm` `itsm`

---

> **TL;DR** — Two Python MCP servers (Salesforce CRM + ServiceNow ITSM) behind a single dev tunnel, orchestrated by one declarative agent — *The Great Trading Company*. Each server renders interactive CRUD widgets directly inside M365 Copilot chat. The agent routes utterances to the right LOB system automatically.

---

## Contents

- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
  - [1. Salesforce MCP Server](#1-salesforce-mcp-server)
  - [2. ServiceNow MCP Server](#2-servicenow-mcp-server)
  - [3. Dev Tunnel (single tunnel, two ports)](#3-dev-tunnel-single-tunnel-two-ports)
  - [4. The Agent — Provision & Sideload](#4-the-agent--provision--sideload)
- [Running](#running)
- [Test Harness](#test-harness)
- [Tools Reference](#tools-reference)
- [Critical Troubleshooting](#critical-troubleshooting)
- [v2.0 Roadmap](#v20-roadmap)
- [References](#references)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        M365 Copilot                             │
│                                                                 │
│  "Show my leads"  ──┐           ┌──  "Show incidents"           │
│                     ▼           ▼                               │
│            ┌────────────────────────────┐                       │
│            │  The Great Trading Company │                       │
│            │   (Declarative Agent)      │                       │
│            │   14 tools · 2 runtimes    │                       │
│            └────┬───────────────┬───────┘                       │
└─────────────────┼───────────────┼───────────────────────────────┘
                  │               │
    ┌─────────────┘               └──────────────┐
    ▼                                            ▼
┌──────────────────┐                ┌──────────────────────┐
│  SF MCP Server   │                │  ServiceNow MCP Srv  │
│  Port 3000       │                │  Port 3001           │
│  6 tools         │                │  8 tools             │
│  Leads, Opps     │                │  Incidents, Requests │
└──────┬───────────┘                └──────┬───────────────┘
       │                                   │
       ▼                                   ▼
   Salesforce                         ServiceNow
   REST API                           Table API
```

**Single Persistent Dev Tunnel** — both servers share one named tunnel (`gtc-tunnel`) with two port mappings. The URL never changes across restarts.

---

## Project Structure

```
lob-mcp-apps/
├── README.md                          ← you are here
│
├── sf-mcp-app/                        # Salesforce CRM MCP server
│   ├── .env.example                   # SF credentials template
│   ├── pyproject.toml
│   ├── sf_crm_mcp/
│   │   ├── server.py                  # 6 tools — Leads & Opportunities CRUD
│   │   ├── salesforce.py              # SF OAuth2 + REST client
│   │   └── web/widget.html            # Interactive CRM widget
│   └── tests/                         # Widget test harness
│
├── snow-mcp-app/                      # ServiceNow ITSM MCP server
│   ├── .env.example                   # ServiceNow credentials template
│   ├── pyproject.toml
│   ├── servicenow_mcp/
│   │   ├── server.py                  # 8 tools — Incidents & Requests CRUD
│   │   └── web/widget.html            # Interactive ServiceNow widget
│   └── tests/                         # Widget test harness
│
└── lob-agent/                         # "The Great Trading Company" agent
    ├── appPackage/
    │   ├── declarativeAgent.json      # Agent identity & conversation starters
    │   ├── manifest.json              # Teams/M365 app manifest
    │   ├── ai-plugin.json             # Two runtimes (SF:3000, SN:3001)
    │   ├── mcp-tools.json             # 14 tools with _meta + widget URIs
    │   └── instruction.txt            # Combined CRM + ITSM persona
    ├── env/.env.dev
    └── m365agents.yml
```

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | ≥ 3.11 |
| Node.js | ≥ 18 (for Teams Toolkit CLI) |
| M365 Agents Toolkit | VS Code extension or `teamsapp` CLI |
| Dev Tunnels CLI | `devtunnel` ([install](https://learn.microsoft.com/azure/developer/dev-tunnels/get-started)) |
| Salesforce Org | Developer Edition or sandbox with a Connected App (OAuth2 client_credentials) |
| ServiceNow Instance | Developer instance with OAuth 2.0 or Basic Auth |
| M365 Developer Tenant | With Copilot license and sideloading enabled |

---

## Setup

### 1. Salesforce MCP Server

```bash
cd sf-mcp-app
cp .env.example .env          # fill in your credentials
```

Edit `.env`:
```env
SF_INSTANCE_URL=https://your-instance.salesforce.com
SF_CLIENT_ID=your-connected-app-client-id
SF_CLIENT_SECRET=your-connected-app-client-secret
PORT=3000
CORS_ORIGINS=*
```

Install dependencies:
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e .
```

### 2. ServiceNow MCP Server

```bash
cd snow-mcp-app
cp .env.example .env          # fill in your credentials
```

Edit `.env`:
```env
SERVICENOW_INSTANCE=dev12345
SERVICENOW_AUTH_MODE=oauth
SERVICENOW_CLIENT_ID=your-client-id
SERVICENOW_CLIENT_SECRET=your-client-secret
PORT=3001
CORS_ORIGINS=*
```

Install dependencies:
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e .
```

### 3. Dev Tunnel (single persistent tunnel, two ports)

Create **one** named persistent tunnel. The URL stays the same across restarts — just don't delete the tunnel:

```bash
# One-time setup
devtunnel create gtc-tunnel --allow-anonymous
devtunnel port create gtc-tunnel -p 3000    # Salesforce MCP server
devtunnel port create gtc-tunnel -p 3001    # ServiceNow MCP server
```

This gives you two **stable** URLs:
- `https://gtc-tunnel-3000.inc1.devtunnels.ms/mcp` → Salesforce
- `https://gtc-tunnel-3001.inc1.devtunnels.ms/mcp` → ServiceNow

To start hosting (every dev session):
```bash
devtunnel host gtc-tunnel
```

> **⚠️ The tunnel name is persistent** — as long as you only _stop_ hosting (Ctrl+C) and don't run `devtunnel delete`, the URLs remain fixed. No need to update `ai-plugin.json` after each restart. Tunnels expire after 30 days of inactivity.

### 4. The Agent — Provision & Sideload

```bash
cd lob-agent
teamsapp provision --env dev
```

Then open M365 Copilot, find **The Great Trading Company** in the agent side panel, and start chatting:
- *"Show me the latest leads"* → Salesforce widget
- *"Show me the latest incidents"* → ServiceNow widget

---

## Running

Start both MCP servers (two terminals):

**Terminal 1 — Salesforce (port 3000)**
```bash
cd sf-mcp-app
.venv\Scripts\activate
python -m sf_crm_mcp
```

**Terminal 2 — ServiceNow (port 3001)**
```bash
cd snow-mcp-app
.venv\Scripts\activate
python -m servicenow_mcp
```

**Terminal 3 — Dev Tunnel**
```bash
devtunnel host gtc-tunnel
```

---

## Test Harness

Each MCP app includes standalone HTML test files that can be opened in a browser to test the widget rendering without M365 Copilot:

- `sf-mcp-app/tests/widget_test.html` — Salesforce CRM widget test
- `snow-mcp-app/tests/widget_test.html` — ServiceNow widget test
- `snow-mcp-app/tests/widget-preview.html` — ServiceNow widget preview

These files mock the MCP host environment and let you iterate on widget HTML/CSS/JS independently.

---

## Tools Reference

### Salesforce CRM (6 tools — port 3000)

| Tool | Description | Required params |
|---|---|---|
| `get_leads` | Latest 5 leads | — |
| `create_lead` | Create a new lead | `last_name`, `company` |
| `update_lead` | Update a lead by Id | `lead_id` |
| `get_opportunities` | Latest 5 opportunities | — |
| `create_opportunity` | Create an opportunity | `name`, `stage`, `close_date` |
| `update_opportunity` | Update an opportunity by Id | `opportunity_id` |

### ServiceNow ITSM (8 tools — port 3001)

| Tool | Description | Required params |
|---|---|---|
| `get_incidents` | Latest incidents | — |
| `get_requests` | Latest service requests | — |
| `get_request_items` | Items for a specific request | `request_sys_id` |
| `create_incident` | Create an incident | `short_description` |
| `create_request` | Create a service request | `short_description` |
| `update_incident` | Update an incident | `sys_id` |
| `update_request` | Update request approval | `sys_id` |
| `update_request_item` | Update item quantity | `sys_id` |

---

## Critical Troubleshooting

If the widget is not rendering in M365 Copilot, check these three things:

1. **`_meta` placement** — The `_meta.ui.resourceUri` must be on the tool definition in `mcp-tools.json`, not nested inside `inputSchema`. This is what tells M365 Copilot to load the widget.

2. **`mcp-tools.json` must match the server** — The tool descriptions in `mcp-tools.json` must exactly mirror what the MCP server returns from `tools/list`. If they drift, regenerate by hitting `POST /mcp` with a `tools/list` request.

3. **`toolOutput` format** — The `structuredContent` returned by each tool must use the `toolOutput` wrapper format that M365 Copilot expects.

4. **Tunnel URLs** — Ensure `ai-plugin.json` has the correct tunnel URLs for both runtimes. Each time you recreate the tunnel, the hostname may change.

5. **Port mismatch** — Salesforce must run on port **3000** and ServiceNow on port **3001**. Verify with `curl http://localhost:3000/mcp` and `curl http://localhost:3001/mcp`.

---

## v2.0 Roadmap

> **v2.0 — SAP Integration** 🚢
>
> The next release of The Great Trading Company will add **SAP S/4HANA** as a third LOB backend — bringing purchase orders, inventory management, and material tracking into the same unified agent. The SAP MCP server will follow the same pattern: a self-contained `sap-mcp-app/` folder with its own widget, test harness, and `.env` configuration, served on a third port through the same dev tunnel.
>
> *The Company's ledger expands — from trade leads and service manifests to the full supply chain.*

---

## References

- [MCP Apps in M365 Copilot](https://learn.microsoft.com/microsoft-365-copilot/extensibility/mcp-apps-overview)
- [FastMCP SDK](https://github.com/jlowin/fastmcp)
- [M365 Agents Toolkit](https://learn.microsoft.com/microsoftteams/platform/toolkit/teams-toolkit-fundamentals)
- [Dev Tunnels Documentation](https://learn.microsoft.com/azure/developer/dev-tunnels/overview)
- [Salesforce REST API](https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/)
- [ServiceNow Table API](https://docs.servicenow.com/bundle/latest/page/integrate/inbound-rest/concept/c_TableAPI.html)
