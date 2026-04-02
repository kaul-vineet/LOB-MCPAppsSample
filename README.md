# ⚓ The Great Trading Company — LOB MCP Apps

<p align="center">
  <em>A colonial trading house for enterprise operations — four LOB systems, one agent, one tunnel</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/🏛️_Salesforce-Trade_Ledger-00A1E0?style=for-the-badge" alt="Salesforce" />
  <img src="https://img.shields.io/badge/🎫_ServiceNow-Service_Manifest-293E40?style=for-the-badge" alt="ServiceNow" />
  <img src="https://img.shields.io/badge/📦_SAP-Cargo_Manifest-0FAAFF?style=for-the-badge" alt="SAP" />
  <img src="https://img.shields.io/badge/🧡_HubSpot-Spice_Bazaar-FF7A59?style=for-the-badge" alt="HubSpot" />
</p>

| | |
|---|---|
| **Subtitle** | A multi-LOB MCP Apps platform for M365 Copilot — Salesforce CRM, ServiceNow ITSM, SAP S/4HANA ERP, and HubSpot CRM in one agent |
| **Author** | Vineet Kaul, PM Architect – Agentic AI, Microsoft |
| **Date** | April 2026 |
| **Stack** | Python · FastMCP 1.26 · Salesforce REST API · ServiceNow Table API · SAP OData · HubSpot REST API · Microsoft Dev Tunnels · M365 Agents Toolkit |

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![MCP SDK](https://img.shields.io/badge/FastMCP-1.26-green)
![M365](https://img.shields.io/badge/M365_Copilot-Public_Preview-orange?logo=microsoft&logoColor=white)
![Salesforce](https://img.shields.io/badge/Salesforce-v62.0-00A1E0?logo=salesforce&logoColor=white)
![ServiceNow](https://img.shields.io/badge/ServiceNow-Table_API-81B5A1?logo=servicenow&logoColor=white)
![SAP](https://img.shields.io/badge/SAP-S%2F4HANA-0FAAFF?logo=sap&logoColor=white)
![HubSpot](https://img.shields.io/badge/HubSpot-CRM-FF7A59?logo=hubspot&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

**Tags:** `mcp` `copilot` `python` `m365` `salesforce` `servicenow` `sap` `hubspot` `agentic-ai` `declarative-agent` `mcp-apps` `crm` `itsm` `erp`

---

> **TL;DR** — Four Python MCP servers (Salesforce CRM + ServiceNow ITSM + SAP S/4HANA + HubSpot CRM) behind a single dev tunnel, orchestrated by one declarative agent — *The Great Trading Company*. Each server renders interactive CRUD widgets directly inside M365 Copilot chat. The agent routes utterances to the right LOB system automatically.

---

## Contents

- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
  - [1. 🏛️ Salesforce](#1-️-salesforce-mcp-server--the-trade-ledger)
  - [2. 🎫 ServiceNow](#2--servicenow-mcp-server--the-service-manifest)
  - [3. 📦 SAP S/4HANA](#3--sap-s4hana-mcp-server--the-cargo-manifest)
  - [4. 🧡 HubSpot](#4--hubspot-crm-mcp-server--the-spice-bazaar)
  - [5. 🚇 Dev Tunnel](#5--dev-tunnel-single-persistent-tunnel-four-ports)
  - [6. ⚓ The Agent](#6--the-agent--provision--sideload)
- [Detailed Setup Guide ↗](SETUP.md)
- [Running](#running)
- [Test Harness](#test-harness)
- [Tools Reference](#tools-reference)
- [Critical Troubleshooting](#critical-troubleshooting)
- [v3.0 Roadmap](#v30-roadmap)
- [References](#references)

> 📖 **New to this?** See [**SETUP.md**](SETUP.md) for a beginner-friendly guide with step-by-step credential setup for every system.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            M365 Copilot                                │
│                                                                        │
│  "Show leads" ──┐    ┌── "Show incidents"    ┌── "Show POs"           │
│                 ▼    ▼                       ▼       ┌── "Show deals" │
│            ┌─────────────────────────────────────────┐▼               │
│            │     The Great Trading Company            │                │
│            │      (Declarative Agent)                 │                │
│            │      26 tools · 4 runtimes               │                │
│            └──┬─────────┬──────────┬──────────┬──────┘                │
└───────────────┼─────────┼──────────┼──────────┼───────────────────────┘
                │         │          │          │
   ┌────────────┘    ┌────┘     ┌────┘     ┌────┘
   ▼                 ▼          ▼          ▼
┌──────────┐  ┌───────────┐  ┌────────┐  ┌─────────┐
│ SF MCP   │  │ SN MCP    │  │SAP MCP │  │ HS MCP  │
│ Port 3000│  │ Port 3001 │  │Port 3002│  │Port 3003│
│ 6 tools  │  │ 8 tools   │  │6 tools │  │6 tools  │
│ Leads    │  │ Incidents │  │POs     │  │Contacts │
│ Opps     │  │ Requests  │  │BPs     │  │Deals    │
└────┬─────┘  └─────┬─────┘  │Matls   │  └────┬────┘
     │              │        └───┬────┘       │
     ▼              ▼            ▼            ▼
 Salesforce    ServiceNow    SAP API      HubSpot
 REST API      Table API     Hub/OData    REST API
```

**Single Persistent Dev Tunnel** — all four servers share one named tunnel (`gtc-tunnel`) with four port mappings. The URL never changes across restarts.

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
├── sap-mcp-app/                       # SAP S/4HANA MCP server
│   ├── .env.example                   # SAP API Hub / tenant credentials
│   ├── pyproject.toml
│   ├── sap_s4hana_mcp/
│   │   ├── server.py                  # 6 tools — POs, Business Partners, Materials
│   │   ├── sap_client.py             # OData client (sandbox + tenant dual-mode)
│   │   └── web/widget.html            # SAP Fiori-inspired widget
│   └── tests/                         # Widget test harness
│
├── hubspot-mcp-app/                   # HubSpot CRM MCP server
│   ├── .env.example                   # HubSpot private app token
│   ├── pyproject.toml
│   ├── hubspot_mcp/
│   │   ├── server.py                  # 6 tools — Contacts & Deals CRUD
│   │   ├── hubspot_client.py          # HubSpot REST client
│   │   └── web/widget.html            # HubSpot-branded widget
│   └── tests/                         # Widget test harness
│
└── lob-agent/                         # "The Great Trading Company" agent
    ├── appPackage/
    │   ├── declarativeAgent.json      # Agent identity & conversation starters
    │   ├── manifest.json              # Teams/M365 app manifest
    │   ├── ai-plugin.json             # 4 runtimes (SF:3000, SN:3001, SAP:3002, HS:3003)
    │   ├── mcp-tools.json             # 26 tools with _meta + widget URIs
    │   └── instruction.txt            # Combined CRM + ITSM + ERP persona
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

| **SAP** | Free account on [api.sap.com](https://api.sap.com) for sandbox API key |
| **HubSpot** | Free CRM account with a Private App token |

---

## Setup

### 1. 🏛️ Salesforce MCP Server — *The Trade Ledger*

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

### 2. 🎫 ServiceNow MCP Server — *The Service Manifest*

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

### 3. 📦 SAP S/4HANA MCP Server — *The Cargo Manifest*

```bash
cd sap-mcp-app
cp .env.example .env          # fill in your API key
```

Edit `.env`:
```env
SAP_MODE=sandbox
SAP_API_KEY=your-api-hub-api-key        # Free from api.sap.com
PORT=3002
CORS_ORIGINS=*
```

> **Sandbox mode** connects to SAP's free API Business Hub — read-only with demo data. Write operations return mock responses. Set `SAP_MODE=tenant` with real credentials for full CRUD.

Install dependencies:
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e .
```

### 4. 🧡 HubSpot CRM MCP Server — *The Spice Bazaar*

```bash
cd hubspot-mcp-app
cp .env.example .env          # fill in your token
```

Edit `.env`:
```env
HUBSPOT_ACCESS_TOKEN=your-private-app-token
PORT=3003
CORS_ORIGINS=*
```

> Create a Private App at: HubSpot → Settings → Integrations → Private Apps. Required scopes: `crm.objects.contacts.read/write`, `crm.objects.deals.read/write`.

Install dependencies:
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e .
```

### 5. 🚇 Dev Tunnel (single persistent tunnel, four ports)

Create **one** named persistent tunnel. The URL stays the same across restarts — just don't delete the tunnel:

```bash
# One-time setup
devtunnel create gtc-tunnel --allow-anonymous
devtunnel port create gtc-tunnel -p 3000    # Salesforce MCP server
devtunnel port create gtc-tunnel -p 3001    # ServiceNow MCP server
devtunnel port create gtc-tunnel -p 3002    # SAP MCP server
devtunnel port create gtc-tunnel -p 3003    # HubSpot MCP server
```

This gives you four **stable** URLs:
- `https://gtc-tunnel-3000.inc1.devtunnels.ms/mcp` → Salesforce
- `https://gtc-tunnel-3001.inc1.devtunnels.ms/mcp` → ServiceNow
- `https://gtc-tunnel-3002.inc1.devtunnels.ms/mcp` → SAP S/4HANA
- `https://gtc-tunnel-3003.inc1.devtunnels.ms/mcp` → HubSpot

To start hosting (every dev session):
```bash
devtunnel host gtc-tunnel
```

> **⚠️ The tunnel name is persistent** — as long as you only _stop_ hosting (Ctrl+C) and don't run `devtunnel delete`, the URLs remain fixed. No need to update `ai-plugin.json` after each restart. Tunnels expire after 30 days of inactivity.

### 6. ⚓ The Agent — Provision & Sideload

```bash
cd lob-agent
teamsapp provision --env dev
```

Then open M365 Copilot, find **The Great Trading Company** in the agent side panel, and start chatting:
- *"Show me the latest leads"* → Salesforce widget
- *"Show me the latest incidents"* → ServiceNow widget
- *"Show me the latest purchase orders"* → SAP widget
- *"Show me the latest contacts"* → HubSpot widget

---

## Running

Start all four MCP servers (four terminals):

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

**Terminal 3 — SAP S/4HANA (port 3002)**
```bash
cd sap-mcp-app
.venv\Scripts\activate
python -m sap_s4hana_mcp
```

**Terminal 4 — HubSpot (port 3003)**
```bash
cd hubspot-mcp-app
.venv\Scripts\activate
python -m hubspot_mcp
```

**Terminal 5 — Dev Tunnel**
```bash
devtunnel host gtc-tunnel
```

---

## Test Harness

Each MCP app includes standalone HTML test files that can be opened in a browser to test the widget rendering without M365 Copilot:

- `sf-mcp-app/tests/widget_test.html` — Salesforce CRM widget test
- `snow-mcp-app/tests/widget_test.html` — ServiceNow widget test
- `snow-mcp-app/tests/widget-preview.html` — ServiceNow widget preview
- `sap-mcp-app/tests/widget_test.html` — SAP S/4HANA widget test
- `hubspot-mcp-app/tests/widget_test.html` — HubSpot CRM widget test

These files mock the MCP host environment and let you iterate on widget HTML/CSS/JS independently.

---

## Tools Reference

### 🏛️ Salesforce CRM (6 tools — port 3000)

| Tool | Description | Required params |
|---|---|---|
| `get_leads` | Latest 5 leads | — |
| `create_lead` | Create a new lead | `last_name`, `company` |
| `update_lead` | Update a lead by Id | `lead_id` |
| `get_opportunities` | Latest 5 opportunities | — |
| `create_opportunity` | Create an opportunity | `name`, `stage`, `close_date` |
| `update_opportunity` | Update an opportunity by Id | `opportunity_id` |

### 🎫 ServiceNow ITSM (8 tools — port 3001)

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

### 📦 SAP S/4HANA (6 tools — port 3002)

| Tool | Description | Required params |
|---|---|---|
| `get_purchase_orders` | Latest purchase orders | — |
| `get_business_partners` | Business partners | — |
| `get_materials` | Materials master data | — |
| `create_purchase_order` | Create a PO | `supplier`, `purchasing_org` |
| `update_purchase_order` | Update a PO | `purchase_order_id` |
| `get_material_details` | Material detail by ID | `material_id` |

> 📡 In sandbox mode, create/update tools return mock demo data.

### 🧡 HubSpot CRM (6 tools — port 3003)

| Tool | Description | Required params |
|---|---|---|
| `get_contacts` | Latest 5 contacts | — |
| `create_contact` | Create a contact | `email`, `firstname`, `lastname` |
| `update_contact` | Update a contact | `contact_id` |
| `get_deals` | Latest 5 deals | — |
| `create_deal` | Create a deal | `dealname`, `pipeline`, `dealstage` |
| `update_deal` | Update a deal | `deal_id` |

---

## Critical Troubleshooting

If the widget is not rendering in M365 Copilot, check these three things:

1. **`_meta` placement** — The `_meta.ui.resourceUri` must be on the tool definition in `mcp-tools.json`, not nested inside `inputSchema`. This is what tells M365 Copilot to load the widget.

2. **`mcp-tools.json` must match the server** — The tool descriptions in `mcp-tools.json` must exactly mirror what the MCP server returns from `tools/list`. If they drift, regenerate by hitting `POST /mcp` with a `tools/list` request.

3. **`toolOutput` format** — The `structuredContent` returned by each tool must use the `toolOutput` wrapper format that M365 Copilot expects.

4. **Tunnel URLs** — Ensure `ai-plugin.json` has the correct tunnel URLs for both runtimes. Each time you recreate the tunnel, the hostname may change.

5. **Port mismatch** — Salesforce must run on port **3000**, ServiceNow on **3001**, SAP on **3002**, and HubSpot on **3003**. Verify with `curl http://localhost:{port}/mcp`.

6. **SAP sandbox mode** — If SAP returns empty results, ensure your `SAP_API_KEY` is valid. Get one free at [api.sap.com](https://api.sap.com) → Log in → Copy API Key from your profile.

---

## v3.0 Roadmap

> **v3.0 — Jira & DocuSign** 🚢
>
> The next expansion of The Great Trading Company will add **Jira** (The Shipwright's Log — epics, sprints, work items) and **DocuSign** (The Royal Seal — contract signing and approval workflows) as fifth and sixth LOB backends.
>
> *The Company's dominion grows — from trade ledgers and cargo manifests to shipyard logs and royal seals.*

---

## References

- [MCP Apps in M365 Copilot](https://learn.microsoft.com/microsoft-365-copilot/extensibility/mcp-apps-overview)
- [FastMCP SDK](https://github.com/jlowin/fastmcp)
- [M365 Agents Toolkit](https://learn.microsoft.com/microsoftteams/platform/toolkit/teams-toolkit-fundamentals)
- [Dev Tunnels Documentation](https://learn.microsoft.com/azure/developer/dev-tunnels/overview)
- [Salesforce REST API](https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/)
- [ServiceNow Table API](https://docs.servicenow.com/bundle/latest/page/integrate/inbound-rest/concept/c_TableAPI.html)
