# ⚓ The Great Trading Company — LOB MCP Apps

<p align="center">
  <em>Six enterprise LOB systems, one M365 Copilot agent, interactive React widgets with side-by-side support</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/🏛️_Salesforce-Lightning_SLDS-00A1E0?style=for-the-badge" alt="Salesforce" />
  <img src="https://img.shields.io/badge/🎫_ServiceNow-Now_Design-293E40?style=for-the-badge" alt="ServiceNow" />
  <img src="https://img.shields.io/badge/📦_SAP-Fiori-0FAAFF?style=for-the-badge" alt="SAP" />
  <img src="https://img.shields.io/badge/🧡_HubSpot-Canvas-FF7A59?style=for-the-badge" alt="HubSpot" />
  <img src="https://img.shields.io/badge/✈️_Flight-OpenSky-1B6CA8?style=for-the-badge" alt="Flight Tracker" />
  <img src="https://img.shields.io/badge/✒️_DocuSign-eSignature-FFB800?style=for-the-badge" alt="DocuSign" />
</p>

| | |
|---|---|
| **Subtitle** | A multi-LOB MCP Apps platform for M365 Copilot — Salesforce CRM, ServiceNow ITSM, SAP S/4HANA ERP, HubSpot Marketing, Flight Tracker, and DocuSign eSignature in one agent |
| **Author** | Vineet Kaul, PM Architect – Agentic AI, Microsoft |
| **Date** | April 2026 |
| **Stack** | Python · FastMCP 1.26 · React 19 · Fluent UI v9 · Vite · @modelcontextprotocol/ext-apps · Docker · Dev Tunnels · M365 Agents Toolkit |

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Fluent UI](https://img.shields.io/badge/Fluent_UI-v9-0078D4?logo=microsoft&logoColor=white)
![MCP SDK](https://img.shields.io/badge/FastMCP-1.26-green)
![MCP Apps](https://img.shields.io/badge/MCP_Apps-ext--apps-purple)
![M365](https://img.shields.io/badge/M365_Copilot-Public_Preview-orange?logo=microsoft&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

**Tags:** `mcp` `mcp-apps` `copilot` `python` `react` `fluent-ui` `m365` `salesforce` `servicenow` `sap` `hubspot` `flight-tracker` `docusign` `agentic-ai` `declarative-agent` `side-by-side` `docker`

---

> **TL;DR** — Six Python MCP servers (Salesforce CRM + ServiceNow ITSM + SAP S/4HANA + HubSpot Marketing + Flight Tracker + DocuSign eSignature) with React + Fluent UI widgets, running in Docker behind a single dev tunnel, orchestrated by one M365 Copilot declarative agent. Each widget renders interactively inside Copilot chat with full CRUD, side-by-side expansion, LOB-native theming, and the official MCP Apps protocol. Flight Tracker and DocuSign ship with **mock mode** — fully functional without credentials.

---

## Contents

- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
  - [1. 🏛️ Salesforce](#1-️-salesforce)
  - [2. 🎫 ServiceNow](#2--servicenow)
  - [3. 📦 SAP S/4HANA](#3--sap-s4hana)
  - [4. 🧡 HubSpot](#4--hubspot)
  - [5. ✈️ Flight Tracker](#5-️-flight-tracker)
  - [6. ✒️ DocuSign](#6-️-docusign)
  - [7. 🚇 Dev Tunnel](#7--dev-tunnel)
  - [8. ⚓ The Agent](#8--the-agent)
- [Detailed Setup Guide ↗](SETUP.md)
- [Running](#running)
- [Mock Mode](#mock-mode)
- [Static Analysis — check_meta.py](#static-analysis--check_metapy)
- [Skills System](#skills-system)
- [Test Harness](#test-harness)
- [Tools Reference](#tools-reference)
- [Critical Troubleshooting](#critical-troubleshooting)
- [References](#references)

> 📖 **New to this?** See [**SETUP.md**](SETUP.md) for a beginner-friendly guide with step-by-step credential setup for every system.

---

## Architecture

### MCP Server vs. MCP App — Why custom servers?

You may wonder: *"Salesforce/ServiceNow/SAP already have (or will have) their own MCP servers — can I just use those?"*

**Short answer: not for widgets.** There's a key difference:

| | Generic MCP Server | MCP App (what we built) |
|---|---|---|
| **Returns** | Raw JSON → LLM summarizes as text | `structuredContent` → renders a **visual widget** |
| **UI** | None — text in chat | Interactive tables with inline Create, Edit, Delete |
| **Requires** | Just tools | Tools + `_meta.ui.resourceUri` + widget HTML resource |
| **Example** | *"You have 5 leads: John Smith at Acme..."* | Live sortable table with ✎ edit buttons |

Our MCP servers are **MCP Apps** — they return structured data that M365 Copilot renders as interactive widgets directly in the chat. A generic LOB MCP server would give you text answers, not visual UI. The widget is the whole point of this project.

> 💡 If a LOB vendor releases their own MCP server and you only need text responses, you can point `ai-plugin.json` at their URL. But for the interactive widget experience, you need the custom servers in this repo.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                M365 Copilot                                    │
│                                                                                │
│  "Show leads"  "Show incidents"  "Show POs"  "Show emails"  "Flights"  "Sign" │
│        └─────────────────────────────┬─────────────────────────────────────┘  │
│                                      ▼                                         │
│                  ┌───────────────────────────────────────────┐                 │
│                  │     The Great Trading Company             │                 │
│                  │      (Declarative Agent)                  │                 │
│                  │      62 tools · 6 runtimes                │                 │
│                  └──┬──────┬──────┬──────┬──────┬───────────┘                 │
└─────────────────────┼──────┼──────┼──────┼──────┼────────────────────────────┘
                      │      │      │      │      │
          ┌───────────┘ ┌────┘  ┌───┘  ┌──┘  ┌───┘
          ▼             ▼       ▼      ▼     ▼          ▼
      ┌────────┐ ┌───────────┐ ┌────────┐ ┌──────┐ ┌────────┐ ┌──────────┐
      │SF MCP  │ │ SN MCP    │ │SAP MCP │ │HSMCP │ │FT MCP  │ │DS MCP    │
      │:3000   │ │ :3001     │ │ :3002  │ │:3003 │ │ :3004  │ │ :3005    │
      │9 tools │ │ 5 tools   │ │6 tools │ │7tools│ │5 tools │ │ 9 tools  │
      └────┬───┘ └─────┬─────┘ └───┬────┘ └──┬───┘ └────┬───┘ └────┬─────┘
           │           │           │          │          │           │
           ▼           ▼           ▼          ▼          ▼           ▼
       Salesforce  ServiceNow   SAP API   HubSpot   OpenSky Net  DocuSign
       REST API    Table API    Hub/OData REST API  REST API     eSign API
```

**Single Persistent Dev Tunnel** — all six servers share one named tunnel (`gtc-tunnel`) with six port mappings. The URL never changes across restarts.

---

## Project Structure

```
lob-mcp-apps/
├── README.md                          ← you are here
├── check_meta.py                      ← static analysis: verifies tool/manifest alignment
│
├── sf-mcp-app/                        # Salesforce CRM MCP server (port 3000)
│   ├── .env.example
│   ├── sf_crm_mcp/
│   │   ├── server.py                  # 9 tools — Leads & Opportunities CRUD + Forms
│   │   ├── salesforce.py              # SF OAuth2 + REST client
│   │   └── web/widget.html
│   └── Dockerfile                     # Multi-stage build
│
├── snow-mcp-app/                      # ServiceNow ITSM MCP server (port 3001)
│   ├── .env.example
│   ├── servicenow_mcp/
│   │   ├── server.py                  # 5 tools — Incidents & Requests
│   │   └── web/widget.html
│   └── Dockerfile
│
├── sap-mcp-app/                       # SAP S/4HANA MCP server (port 3002)
│   ├── .env.example
│   ├── sap_s4hana_mcp/
│   │   ├── server.py                  # 6 tools — POs, Business Partners, Materials
│   │   ├── sap_client.py
│   │   └── web/widget.html
│   └── Dockerfile
│
├── hubspot-mcp-app/                   # HubSpot CRM MCP server (port 3003)
│   ├── .env.example
│   ├── hubspot_mcp/
│   │   ├── server.py                  # 7 tools — Emails, Lists & Contacts
│   │   ├── hubspot_client.py
│   │   └── web/widget.html
│   └── Dockerfile
│
├── flight-mcp-app/                    # Flight Tracker MCP server (port 3004)
│   ├── .env.example                   # OpenSky credentials (optional — mock mode if absent)
│   ├── flight_mcp/
│   │   ├── server.py                  # 5 tools — departures, arrivals, aircraft state/track
│   │   └── web/widget.html
│   └── Dockerfile
│
├── docusign-mcp-app/                  # DocuSign eSignature MCP server (port 3005)
│   ├── .env.example                   # DocuSign JWT credentials (optional — mock mode if absent)
│   ├── docusign_mcp/
│   │   ├── server.py                  # 9 tools — envelopes, templates, send, void, sign
│   │   └── web/widget.html
│   └── Dockerfile
│
└── lob-agent/                         # "The Great Trading Company" agent
    ├── appPackage/
    │   ├── declarativeAgent.json      # Agent identity & 10 conversation starters
    │   ├── manifest.json
    │   ├── ai-plugin.json             # 6 runtimes (SF:3000, SN:3001, SAP:3002, HS:3003, FT:3004, DS:3005)
    │   ├── mcp-tools.json             # Tool schemas with _meta + widget URIs
    │   └── instruction.txt            # Combined persona across all 6 LOBs
    ├── skills/                        # Per-LOB scenario documentation
    │   ├── crm-pipeline.md
    │   ├── incident-triage.md
    │   ├── procurement-check.md
    │   ├── campaign-performance.md
    │   ├── flight-tracker.md
    │   ├── docusign-envelopes.md
    │   └── cross-lob-operations.md
    ├── env/.env.dev
    └── m365agents.yml
```

---

## Prerequisites

| Requirement | Version |
|---|---|
| **Docker Desktop** | Latest ([install](https://docker.com/products/docker-desktop)) — **recommended**, eliminates Python/venv setup |
| Python | ≥ 3.11 *(only if not using Docker)* |
| Node.js | ≥ 18 (for Teams Toolkit CLI) |
| M365 Agents Toolkit | VS Code extension or `teamsapp` CLI |
| Dev Tunnels CLI | `devtunnel` ([install](https://learn.microsoft.com/azure/developer/dev-tunnels/get-started)) |
| Salesforce Org | Developer Edition or sandbox with a Connected App (OAuth2 client_credentials) |
| ServiceNow Instance | Developer instance with OAuth 2.0 or Basic Auth |
| SAP | Free account on [api.sap.com](https://api.sap.com) for sandbox API key |
| HubSpot | Free CRM account with a Private App token |
| OpenSky Network | Free account for Flight Tracker credentials *(optional — mock mode works without)* |
| DocuSign | Developer sandbox account with JWT Grant app *(optional — mock mode works without)* |
| M365 Developer Tenant | With Copilot license and sideloading enabled |

---

## Setup

### 1. Clone & Configure Credentials

```bash
git clone https://github.com/kaul-vineet/LOB-MCPAppsSample.git
cd lob-mcp-apps
```

Copy `.env.example` → `.env` for each app and fill in credentials:

```bash
cp sf-mcp-app/.env.example sf-mcp-app/.env
cp snow-mcp-app/.env.example snow-mcp-app/.env
cp sap-mcp-app/.env.example sap-mcp-app/.env
cp hubspot-mcp-app/.env.example hubspot-mcp-app/.env
cp flight-mcp-app/.env.example flight-mcp-app/.env
cp docusign-mcp-app/.env.example docusign-mcp-app/.env
```

### 1. 🏛️ Salesforce

| Key credential | How to get |
|---|---|
| `SF_INSTANCE_URL` | Your Salesforce org URL (e.g. `https://myorg.salesforce.com`) |
| `SF_CLIENT_ID`, `SF_CLIENT_SECRET` | Setup → App Manager → New Connected App → OAuth2 client_credentials |

### 2. 🎫 ServiceNow

| Key credential | How to get |
|---|---|
| `SERVICENOW_INSTANCE` | Your instance hostname (e.g. `dev12345.service-now.com`) |
| `SERVICENOW_CLIENT_ID/SECRET` or `USERNAME/PASSWORD` | Developer instance from [developer.servicenow.com](https://developer.servicenow.com). Set `AUTH_MODE=oauth` or `AUTH_MODE=basic` |

### 3. 📦 SAP S/4HANA

| Key credential | How to get |
|---|---|
| `SAP_API_KEY` | Free from [api.sap.com](https://api.sap.com) → Log in → Copy API Key. Uses sandbox by default |

### 4. 🧡 HubSpot

| Key credential | How to get |
|---|---|
| `HUBSPOT_ACCESS_TOKEN` | Settings → Integrations → Private Apps. Scopes: `crm.objects.contacts.read/write` |

### 5. ✈️ Flight Tracker

> **No credentials required** — set `MOCK_MODE=true` or leave credentials blank to use realistic mock data. See [Mock Mode](#mock-mode).

| Key credential | How to get |
|---|---|
| `OPENSKY_CLIENT_ID`, `OPENSKY_CLIENT_SECRET` | Free account at [opensky-network.org](https://opensky-network.org) |

### 6. ✒️ DocuSign

> **No credentials required** — set `MOCK_MODE=true` or leave credentials blank for mock envelopes. See [Mock Mode](#mock-mode).

| Key credential | How to get |
|---|---|
| `DOCUSIGN_INTEGRATION_KEY` | DocuSign Developer → Apps → Add App → Authorization Code Grant |
| `DOCUSIGN_USER_ID`, `DOCUSIGN_ACCOUNT_ID` | From your DocuSign developer account |
| `DOCUSIGN_PRIVATE_KEY_PATH` | RSA private key file path for JWT Grant |
| `DOCUSIGN_BASE_URL` | Demo URL: `https://demo.docusign.net/restapi` |

### 7. 🚇 Dev Tunnel (one-time setup)

```bash
devtunnel user login -d
devtunnel create gtc-tunnel --allow-anonymous
devtunnel port create gtc-tunnel -p 3000    # Salesforce
devtunnel port create gtc-tunnel -p 3001    # ServiceNow
devtunnel port create gtc-tunnel -p 3002    # SAP
devtunnel port create gtc-tunnel -p 3003    # HubSpot
devtunnel port create gtc-tunnel -p 3004    # Flight Tracker
devtunnel port create gtc-tunnel -p 3005    # DocuSign
```

Note the tunnel hostname and update `lob-agent/appPackage/ai-plugin.json` with the URLs.

> **⚠️ `--allow-anonymous` is required** on both `create` and `host` — without it, M365 Copilot's backend servers cannot reach your MCP endpoints through the tunnel.

### 8. ⚓ Agent Provisioning

Requires VS Code + [M365 Agents Toolkit](https://marketplace.visualstudio.com/items?itemName=TeamsDevApp.ms-teams-vscode-extension) v6.6.1+.

1. Open `lob-agent/` folder in VS Code
2. ATK sidebar → **Accounts** → sign in to M365. Verify both **Custom App Upload Enabled ✓** and **Copilot Access Enabled ✓**
3. ATK sidebar → **Lifecycle** → **Provision**

Or via CLI:
```bash
cd lob-agent
teamsapp auth login m365
teamsapp provision --env dev
```

---

## Running

### Option A: One-Command Startup (Recommended) ⚡

```powershell
.\Set-Sail.ps1                          # Docker + tunnel (default)
.\Set-Sail.ps1 -Native                  # Python venvs + tunnel
.\Set-Sail.ps1 -SkipTunnel              # Docker only, no tunnel
.\Set-Sail.ps1 -TunnelName my-tunnel    # Use a specific named tunnel
.\Set-Sail.ps1 -Only sf,sap             # Start specific services only
```

### Option B: Docker Manual 🐳

```bash
docker compose up -d

devtunnel host gtc-tunnel --allow-anonymous

docker compose ps
docker compose logs -f
docker compose down
```

### Option C: Python Venvs (for development)

```bash
cd sf-mcp-app   && python -m venv .venv && .venv\Scripts\activate && pip install -e . && python -m sf_crm_mcp         # :3000
cd snow-mcp-app && python -m venv .venv && .venv\Scripts\activate && pip install -e . && python -m servicenow_mcp     # :3001
cd sap-mcp-app  && python -m venv .venv && .venv\Scripts\activate && pip install -e . && python -m sap_s4hana_mcp     # :3002
cd hubspot-mcp-app && python -m venv .venv && .venv\Scripts\activate && pip install -e . && python -m hubspot_mcp     # :3003
cd flight-mcp-app  && python -m venv .venv && .venv\Scripts\activate && pip install -e . && python -m flight_mcp      # :3004
cd docusign-mcp-app && python -m venv .venv && .venv\Scripts\activate && pip install -e . && python -m docusign_mcp   # :3005
```

---

## Mock Mode

**Flight Tracker** and **DocuSign** ship with full mock support — no credentials required to demo them.

Mock mode activates automatically when credentials are absent, or can be forced explicitly:

```bash
# Force mock mode via environment variable
MOCK_MODE=true

# Or simply omit credentials — servers detect missing config and fall back to mock data
```

| Server | Mock triggers | What you get |
|--------|--------------|--------------|
| **Flight Tracker** | `MOCK_MODE=true` or missing `OPENSKY_CLIENT_ID` | 5 GTC-themed flights: Dubai→London, etc. Aircraft states with realistic positions |
| **DocuSign** | `MOCK_MODE=true` or `_validate_env()` returns an error | 5 mock envelopes (NDA sent, GTC completed, MSA voided…), 4 templates |

When mock mode is active, all tools work normally — the agent and widget see the same response shape as with real credentials. Mock data is GTC-themed with realistic field values.

---

## Static Analysis — check_meta.py

`check_meta.py` at the project root validates that your tool definitions stay in sync across the three files that must agree:

- `lob-agent/appPackage/mcp-tools.json` — tool schemas with `_meta` widget URIs
- `lob-agent/appPackage/ai-plugin.json` — tool registration for M365 Copilot
- Each `server.py` — actual tools the server exposes at runtime

```bash
python check_meta.py              # quick check — exits 1 if drift detected
python check_meta.py --verbose    # full report with per-tool status
```

**What it checks:**

| Check | Description |
|-------|-------------|
| `_meta` presence | Every tool in `mcp-tools.json` has `_meta.ui.resourceUri` (required for widget rendering) |
| Plugin registration | Every tool in `mcp-tools.json` is registered in `ai-plugin.json` |
| Server drift | Tools in `server.py` are declared in `mcp-tools.json` (catches stale manifest) |

Run this after adding tools or updating `server.py` to catch drift before it reaches Copilot.

---

## Skills System

`lob-agent/skills/` documents per-LOB scenario prompts — starter conversations for each line of business:

| File | LOB | Example starter |
|------|-----|----------------|
| `crm-pipeline.md` | Salesforce | *"Show me the latest leads. I want to review and update qualified ones."* |
| `incident-triage.md` | ServiceNow | *"Show me open incidents sorted by priority."* |
| `procurement-check.md` | SAP | *"Show me recent purchase orders and check stock for order 4500000001."* |
| `campaign-performance.md` | HubSpot | *"Which campaigns have the best open rates?"* |
| `flight-tracker.md` | Flight Tracker | *"Show me departures from Heathrow today."* |
| `docusign-envelopes.md` | DocuSign | *"Show me envelopes awaiting signature."* |
| `cross-lob-operations.md` | All | *"Give me an end-of-day operations check."* |

These map directly to the 10 conversation starters in `declarativeAgent.json`.

---

## Demo Screens & Prompts

### Salesforce CRM (port 3000)

| Screen | Prompt |
|--------|--------|
| Leads table | "Show me the latest leads" |
| Opportunities table | "Show me the latest opportunities" |
| Create lead | "Create a new lead for Sarah Chen at CloudBase Corp" |
| Edit lead | Click ✏️ on any row in the widget |
| Create opportunity | "Create an opportunity for Acme deal, Prospecting stage, closing June 30" |

### ServiceNow ITSM (port 3001)

| Screen | Prompt |
|--------|--------|
| Incidents table | "Show me open incidents" |
| Requests table | "Show me service requests" |
| Create incident | "Raise a VPN incident for Building A" |
| Edit incident | Click ✏️ on any row |

### SAP S/4HANA (port 3002)

| Screen | Prompt |
|--------|--------|
| Purchase Orders | "Show me recent purchase orders" |
| Business Partners | "Show me suppliers" |
| Materials | "Show me materials inventory" |
| Material detail | Click "View Detail" on any row |
| Create PO | "Create a PO for Domestic US Supplier 1" |

### HubSpot Marketing (port 3003)

| Screen | Prompt |
|--------|--------|
| Emails + metric cards | "Show me marketing email performance" |
| Contact Lists | Click "View Lists" in the widget |
| Contacts in list | Click "View Contacts" on any list |
| Add / remove contact | Click "+ Add Contact" in the contacts view |

### Flight Tracker (port 3004)

| Screen | Prompt |
|--------|--------|
| Airport departures | "Show me departures from Heathrow (EGLL) today" |
| Airport arrivals | "Show me arrivals at JFK yesterday" |
| Live aircraft state | "What is the live state of aircraft 4ca2bf?" |
| Flight history | "Show me flight history for 4ca2bf over the last two days" |
| Flight track | "Show me the track for aircraft 3c675a" |

> Works out-of-the-box with mock data — no OpenSky credentials required.

### DocuSign eSignature (port 3005)

| Screen | Prompt |
|--------|--------|
| Envelope list | "Show me my DocuSign envelopes" |
| Awaiting signature | "Show me envelopes awaiting signature" |
| Envelope detail | "Show me the details of envelope env-0002-gtc" |
| Templates | "List my signing templates" |
| Send envelope | "Send the NDA template to james@gtc.internal for signature" |
| Void envelope | "Void envelope env-0004-gtc — terms have changed" |

> Works out-of-the-box with mock data — no DocuSign credentials required.

### Cross-LOB Workflows

| Workflow | Prompt |
|----------|--------|
| Multi-LOB customer check | "Check on Acme" → SF leads + SNOW incidents |
| Operations summary | "Give me an end-of-day operations check" → leads + incidents + POs |
| Create across LOBs | "Log a lead for John at TechCorp and raise a VPN incident" |
| Prospect onboarding | "Create a lead for Sarah Chen at CloudBase, raise a VPN access ticket, and send the NDA for signature" |
| Side-by-side mode | Click "⤢ Expand" in any widget header |

---

## Tools Reference

### 🏛️ Salesforce CRM (9 tools — port 3000)

| Tool | Description | Required params |
|---|---|---|
| `sf__get_leads` | Latest 5 leads | — |
| `sf__create_lead` | Create a new lead | `last_name`, `company` |
| `sf__update_lead` | Update a lead | `lead_id` |
| `sf__get_opportunities` | Latest 5 opportunities | — |
| `sf__create_opportunity` | Create an opportunity | `name`, `stage`, `close_date` |
| `sf__update_opportunity` | Update an opportunity | `opportunity_id` |
| `sf__get_lead_form` | Empty lead creation form | — |
| `sf__get_opportunity_form` | Empty opportunity creation form | — |
| `sf__submit_form` | Submit any form | `form_id`, `fields` |

### 🎫 ServiceNow ITSM (5 tools — port 3001)

| Tool | Description | Required params |
|---|---|---|
| `sn__get_incidents` | Latest incidents | — |
| `sn__get_requests` | Latest service requests | — |
| `sn__create_incident` | Create an incident | `short_description` |
| `sn__update_incident` | Update an incident | `sys_id` |
| `sn__get_request_items` | Items for a request | `request_sys_id` |

### 📦 SAP S/4HANA (6 tools — port 3002)

| Tool | Description | Required params |
|---|---|---|
| `sap__get_purchase_orders` | Latest purchase orders | — |
| `sap__get_business_partners` | Business partners | — |
| `sap__get_materials` | Materials master data | — |
| `sap__create_purchase_order` | Create a PO | `supplier`, `purchasing_org` |
| `sap__update_purchase_order` | Update a PO | `purchase_order_id` |
| `sap__get_material_details` | Material detail by ID | `material_id` |

> In sandbox mode, create/update return mock demo data.

### 🧡 HubSpot Marketing (7 tools — port 3003)

| Tool | Description | Called by |
|---|---|---|
| `hs__get_emails` | Marketing emails with stats | LLM (entry point) |
| `hs__get_lists` | Contact lists/segments | Widget |
| `hs__get_list_contacts` | Contacts in a list | Widget |
| `hs__add_to_list` | Add contact to list | Widget |
| `hs__remove_from_list` | Remove contact from list | Widget |
| `hs__update_email` | Edit email name/subject | Widget |
| `hs__update_list` | Edit list name | Widget |

> The LLM only calls `get_emails`. The widget handles Emails → Lists → Contacts → Add/Remove/Edit.

### ✈️ Flight Tracker (5 tools — port 3004)

| Tool | Description | Required params |
|---|---|---|
| `ft__get_airport_departures` | Departures from an ICAO airport | `airport` (e.g. `EGLL`) |
| `ft__get_airport_arrivals` | Arrivals at an ICAO airport | `airport`, `begin`, `end` |
| `ft__get_aircraft_state` | Live position/speed/altitude | `icao24` |
| `ft__get_flights_by_aircraft` | Flight history for an aircraft | `icao24`, `begin`, `end` |
| `ft__get_aircraft_track` | Waypoints for a specific flight | `icao24` |

### ✒️ DocuSign eSignature (9 tools — port 3005)

| Tool | Description | Required params |
|---|---|---|
| `get_envelopes` | List envelopes with status | — |
| `get_envelope_details` | Recipient/signing progress detail | `envelope_id` |
| `get_templates` | Available signing templates | — |
| `send_envelope` | Send envelope from template | `template_id`, `recipient_email`, `recipient_name` |
| `send_envelope_form` | Interactive send form | — |
| `void_envelope` | Void an envelope | `envelope_id`, `void_reason` |
| `resend_envelope` | Resend to pending recipients | `envelope_id` |
| `get_signing_url` | Embedded signing URL | `envelope_id`, `recipient_email` |
| `download_document` | Download signed document | `envelope_id` |

---

## Widget Architecture

React 19 + Fluent UI v9 widgets compiled into single-file HTML via Vite, using the official `@modelcontextprotocol/ext-apps` package. Each widget is styled to match its LOB's native design language:

| Widget | Design System | Key Visual Elements |
|--------|--------------|-------------------|
| **Salesforce** | Lightning (SLDS) | Blue header, pill status badges, compact CRUD forms, flash-on-save |
| **SAP** | Fiori | Shell bar, '72' font, semantic badges, Object Page layout |
| **HubSpot** | Canvas | Metric cards, percentage bars, coral/teal palette, 3-level drill-down |
| **ServiceNow** | Now Design | Teal shell, P1-P4 priority colors, expandable request rows |
| **Flight Tracker** | Fluent v9 | Dark sky theme, live status badges, altitude/speed metrics |
| **DocuSign** | DocuSign brand | Envelope status cards, signer progress, send/void actions |

### Platform features

| Feature | Implementation |
|---------|---------------|
| **MCP Apps protocol** | `@modelcontextprotocol/ext-apps` — official handshake, tool-result delivery |
| **Side-by-side mode** | `app.requestDisplayMode('fullscreen')` |
| **Auto theming** | Light/dark via host context — FluentProvider + LOB brand overrides |
| **Skeleton loading** | CSS shimmer animation while data loads |
| **Error boundaries** | Widget crashes show recovery UI with "Try Again" button |
| **CRUD operations** | Create, read, update across all 6 LOB systems |
| **Toast notifications** | Success/error feedback after save operations |
| **Multi-stage Docker** | Builder → runtime images — smaller final images, faster CI rebuilds |

### Dockerfiles — multi-stage pattern

All six Dockerfiles use a two-stage build to keep images small:

```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY pyproject.toml .
COPY {pkg}/ {pkg}/
RUN pip install --no-cache-dir .

FROM python:3.11-slim AS runtime
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
EXPOSE {port}
CMD ["python", "-m", "{module}"]
```

The builder stage installs all dependencies into a venv; the runtime stage copies only the venv — no build tools in production.

---

## Logs & Monitoring

```bash
docker compose logs -f                  # all servers
docker compose logs -f salesforce       # port 3000
docker compose logs -f servicenow       # port 3001
docker compose logs -f sap              # port 3002
docker compose logs -f hubspot          # port 3003
docker compose logs -f flight           # port 3004
docker compose logs -f docusign         # port 3005
docker compose logs --tail 50 flight
```

| Log entry | Meaning |
|-----------|---------|
| `POST /mcp HTTP/1.1 200 OK` | MCP request succeeded |
| `Processing request of type CallToolRequest` | A tool was called |
| `Processing request of type ReadResourceRequest` | Widget HTML was fetched |
| `[MOCK]` prefix in server log | Mock mode is active |

---

## Critical Troubleshooting

1. **MCP Apps handshake** — The widget must send `ui/initialize` (with `appInfo` and `appCapabilities`) via `postMessage`, wait for the host response, then send `ui/notifications/initialized`. Only then will the host deliver `ui/notifications/tool-result`.

2. **`--allow-anonymous` on the tunnel** — Both `devtunnel create` and `devtunnel host` must include `--allow-anonymous`.

3. **`_meta` placement** — `_meta.ui.resourceUri` must be on the tool definition in `mcp-tools.json`, not nested inside `inputSchema`.

4. **`mcp-tools.json` must match the server** — Run `python check_meta.py` to surface drift between manifest and server tools.

5. **`callTool` method name** — Widget-to-host calls must use `method: 'tools/call'` with `arguments`.

6. **Custom App Upload Enabled** — ATK sidebar → Accounts. Both "Custom App Upload Enabled" and "Copilot Access Enabled" must show ✓.

7. **Tunnel URLs** — Ensure `ai-plugin.json` has the correct tunnel URLs for all 6 runtimes.

8. **Port mapping** — SF:3000, SN:3001, SAP:3002, HS:3003, FT:3004, DS:3005. Verify with `curl http://localhost:{port}/mcp`.

9. **Flight/DocuSign not showing data** — Check if mock mode is active: `MOCK_MODE=true` or verify credentials in `.env`. Both LOBs work fully in mock mode.

---

## 🧰 Using This as a Scaffolding

Fork and copy any app folder as a template. Recommended starting points:

- `sf-mcp-app/` — full CRUD with forms
- `sap-mcp-app/` — read-heavy with mock writes
- `flight-mcp-app/` — read-only with mock fallback pattern

### Adding a new LOB

1. Copy an app folder and rename the Python package
2. Replace the API client with your LOB's auth + REST calls
3. Rewrite `server.py` tools — keep `@mcp.tool(meta={"ui": {"resourceUri": WIDGET_URI}})` and `structuredContent` returns
4. Build your widget from an existing one as template
5. Add to `ai-plugin.json` (new runtime block) and `mcp-tools.json` (tool schemas with `_meta`)
6. Add a tunnel port: `devtunnel port create gtc-tunnel -p 300X`
7. Run `python check_meta.py` to verify alignment

### Key patterns to preserve

| Pattern | Why it matters |
|---|---|
| `_meta.ui.resourceUri` on every tool | M365 Copilot loads the widget from this URI |
| `structuredContent` in every response | The widget reads this JSON to render data |
| `get_settings()` with `@lru_cache(maxsize=1)` | Settings constructed once; testable via `reset_settings_cache()` |
| `_load_env()` discovery chain | `MCP_SERVERS_ENV_FILE` → `env/.env.{lob}` → `.env` |
| `_is_mock()` guard | Graceful no-credential fallback for demo/dev environments |
| Multi-stage Dockerfile | Small runtime images; build tools not shipped to prod |

---

## References

- [MCP Apps in M365 Copilot](https://learn.microsoft.com/microsoft-365-copilot/extensibility/mcp-apps-overview)
- [FastMCP SDK](https://github.com/jlowin/fastmcp)
- [M365 Agents Toolkit](https://learn.microsoft.com/microsoftteams/platform/toolkit/teams-toolkit-fundamentals)
- [Dev Tunnels Documentation](https://learn.microsoft.com/azure/developer/dev-tunnels/overview)
- [Salesforce REST API](https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/)
- [ServiceNow Table API](https://docs.servicenow.com/bundle/latest/page/integrate/inbound-rest/concept/c_TableAPI.html)
- [OpenSky Network API](https://openskynetwork.github.io/opensky-api/)
- [DocuSign eSignature REST API](https://developers.docusign.com/docs/esign-rest-api/)
