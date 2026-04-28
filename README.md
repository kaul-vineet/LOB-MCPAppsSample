# Enterprise LOB Copilot MCP Apps

<p align="center">
  <em>Ten enterprise LOB systems, one M365 Copilot agent, interactive React widgets with side-by-side support</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/🏛️_Salesforce-Lightning_SLDS-00A1E0?style=for-the-badge" alt="Salesforce" />
  <img src="https://img.shields.io/badge/🎫_ServiceNow-Now_Design-293E40?style=for-the-badge" alt="ServiceNow" />
  <img src="https://img.shields.io/badge/📦_SAP_S4HANA-Fiori-0FAAFF?style=for-the-badge" alt="SAP" />
  <img src="https://img.shields.io/badge/🧡_HubSpot-Canvas-FF7A59?style=for-the-badge" alt="HubSpot" />
  <img src="https://img.shields.io/badge/✈️_Flight-OpenSky-1B6CA8?style=for-the-badge" alt="Flight Tracker" />
  <img src="https://img.shields.io/badge/✒️_DocuSign-eSignature-FFB800?style=for-the-badge" alt="DocuSign" />
  <img src="https://img.shields.io/badge/👤_SAP_SF-SuccessFactors-0070B1?style=for-the-badge" alt="SAP SuccessFactors" />
  <img src="https://img.shields.io/badge/💼_Workday-HCM-F5901E?style=for-the-badge" alt="Workday" />
  <img src="https://img.shields.io/badge/🛒_Coupa-Procurement-E3291B?style=for-the-badge" alt="Coupa" />
  <img src="https://img.shields.io/badge/📋_Jira-Projects-0052CC?style=for-the-badge" alt="Jira" />
</p>

| | |
|---|---|
| **Subtitle** | A multi-LOB MCP Apps platform for M365 Copilot — 10 enterprise systems, 225 tools, 6 React widgets in one agent |
| **Author** | Vineet Kaul, PM Architect – Agentic AI, Microsoft |
| **Date** | April 2026 |
| **Stack** | Python · FastMCP 1.26 · React 19 · Fluent UI v9 · Vite · @modelcontextprotocol/ext-apps · Docker · Dev Tunnels · M365 Agents Toolkit · Azure Container Apps |

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Fluent UI](https://img.shields.io/badge/Fluent_UI-v9-0078D4?logo=microsoft&logoColor=white)
![MCP SDK](https://img.shields.io/badge/FastMCP-1.26-green)
![MCP Apps](https://img.shields.io/badge/MCP_Apps-ext--apps-purple)
![M365](https://img.shields.io/badge/M365_Copilot-Public_Preview-orange?logo=microsoft&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Azure](https://img.shields.io/badge/Azure-Container_Apps-0078D4?logo=microsoftazure&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

**Tags:** `mcp` `mcp-apps` `copilot` `python` `react` `fluent-ui` `m365` `salesforce` `servicenow` `sap` `hubspot` `flight-tracker` `docusign` `sap-successfactors` `workday` `coupa` `jira` `agentic-ai` `declarative-agent` `azure-container-apps` `bicep`

---

> **TL;DR** — Ten Python MCP servers (Salesforce CRM · ServiceNow ITSM · SAP S/4HANA · HubSpot Marketing · Flight Tracker · DocuSign eSignature · SAP SuccessFactors HR · Workday HCM · Coupa Procurement · Jira Projects) with React + Fluent UI widgets, running behind a single ASGI gateway (port 8080) or via Docker Compose, orchestrated by one M365 Copilot declarative agent with 225 tools across 10 runtimes. All new LOBs (and Flight/DocuSign) ship with **mock mode** — fully functional without credentials. Deploy to Azure Container Apps with one Bicep file.

---

## Contents

- [Architecture](#architecture)
- [LOBs at a Glance](#lobs-at-a-glance)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running](#running)
  - [Option A: Gateway (Recommended)](#option-a-asgi-gateway-recommended-)
  - [Option B: Docker Compose](#option-b-docker-compose-)
  - [Option C: Python Venvs](#option-c-python-venvs-dev)
- [Deploy to Azure](#deploy-to-azure)
- [Mock Mode](#mock-mode)
- [Static Analysis — check_meta.py](#static-analysis--check_metapy)
- [Manifest Generation — regen_manifests.py](#manifest-generation--regen_manifestspy)
- [Skills System](#skills-system)
- [Tools Reference](#tools-reference)
- [Widget Architecture](#widget-architecture)
- [Logs & Monitoring](#logs--monitoring)
- [Telemetry — App Insights](#telemetry--app-insights)
- [Critical Troubleshooting](#critical-troubleshooting)
- [References](#references)

> 📖 **New to this?** See [**SETUP.md**](SETUP.md) for a beginner-friendly step-by-step credential guide.

---

## Architecture

### MCP Server vs. MCP App — Why custom servers?

| | Generic MCP Server | MCP App (what we built) |
|---|---|---|
| **Returns** | Raw JSON → LLM summarizes as text | `structuredContent` → renders a **visual widget** |
| **UI** | None — text in chat | Interactive tables with inline Create, Edit, Delete |
| **Requires** | Just tools | Tools + `_meta.ui.resourceUri` + widget HTML resource |
| **Example** | *"You have 5 leads: John Smith at Acme..."* | Live sortable table with ✎ edit buttons |

Our MCP servers are **MCP Apps** — they return structured data that M365 Copilot renders as interactive widgets directly in the chat.

```
┌──────────────────────────────────────────────────────────────────────┐
│                           M365 Copilot                               │
│                                                                      │
│  "Show leads"  "Open incidents"  "POs"  "Flights"  "Sign"  "HR"    │
│        └───────────────────────────┬──────────────────────────────┘  │
│                                    ▼                                  │
│         ┌─────────────────────────────────────────────────┐          │
│         │      Enterprise LOB Copilot (Declarative Agent) │          │
│         │         225 tools · 10 runtimes                 │          │
│         └──┬──┬──┬──┬──┬──┬──┬──┬──┬──────────────────────┘          │
└────────────┼──┼──┼──┼──┼──┼──┼──┼──┼──────────────────────────────┘
             │  │  │  │  │  │  │  │  │
             ▼  ▼  ▼  ▼  ▼  ▼  ▼  ▼  ▼  ▼
   ┌───────────────────────────────────────────────────────────────┐
   │         ASGI Gateway  :8080  (all 10 LOBs in-process)        │
   │  /sf  /sn  /sap  /hs  /ft  /ds  /saphr  /workday  /coupa  /jira │
   └───────────────────────────────────────────────────────────────┘
```

**Two deployment modes:**
- **Gateway** — all 10 LOBs in one Python process on port 8080 (dev tunnel / Azure Container Apps)
- **Docker Compose** — 10 individual services on ports 3000–3009 (optional per-LOB isolation)

---

## LOBs at a Glance

| # | LOB | Port | Tools | Widget | Mock Mode |
|---|-----|------|-------|--------|-----------|
| 1 | 🏛️ Salesforce CRM | 3000 | 31 | ✅ React + Fluent UI | — |
| 2 | 🎫 ServiceNow ITSM | 3001 | 24 | ✅ React + Fluent UI | — |
| 3 | 📦 SAP S/4HANA | 3002 | 14 | ✅ React + Fluent UI | sandbox default |
| 4 | 🧡 HubSpot Marketing | 3003 | 29 | ✅ React + Fluent UI | — |
| 5 | ✈️ Flight Tracker | 3004 | 5 | ✅ React + Fluent UI | ✅ auto if no creds |
| 6 | ✒️ DocuSign eSignature | 3005 | 9 | ✅ React + Fluent UI | ✅ auto if no creds |
| 7 | 👤 SAP SuccessFactors HR | 3006 | 20 | ⬜ pending | ✅ auto if no creds |
| 8 | 💼 Workday HCM | 3007 | 46 | ⬜ pending | ✅ auto if no creds |
| 9 | 🛒 Coupa Procurement | 3008 | 21 | ⬜ pending | ✅ always (COUPA_MOCK=true) |
| 10 | 📋 Jira Projects | 3009 | 26 | ⬜ pending | ✅ auto if no creds |
| | **Gateway** | **8080** | **225** | | |

---

## Project Structure

```
lob-mcp-apps/
├── README.md
├── .gitignore
├── check_meta.py              ← static analysis: tool/manifest alignment
├── regen_manifests.py         ← regenerate mcp-tools.json + ai-plugin.json
│
├── shared-mcp-lib/            # Shared auth/HTTP/logging/telemetry/settings helpers
│   └── shared_mcp/
│       ├── auth.py            # get_bearer_token(ctx) — OAuth Bearer extraction
│       ├── http.py            # create_async_client() — httpx factory
│       ├── logger.py          # get_logger() — structlog wrapper
│       ├── settings.py        # Dataclass loaders for saphr/workday/coupa/jira
│       └── telemetry.py       # track_tool() decorator + wrap_specs() — App Insights
│
├── sf-mcp-app/                # Salesforce CRM (port 3000)
│   ├── sf_crm_mcp/
│   │   ├── salesforce_server.py  # 31 tools — Leads, Opps, Accounts, Contacts,
│   │   │                         #   Cases, Tasks, Pipeline, Campaigns, Approvals
│   │   ├── salesforce.py         # OAuth2 + REST client (query/create/update/delete)
│   │   └── web/widget.html       # React + SLDS widget
│   └── .env.example
│
├── snow-mcp-app/              # ServiceNow ITSM (port 3001)
│   ├── servicenow_mcp/
│   │   ├── servicenow_server.py  # 24 tools — Incidents, Requests, Change Requests,
│   │   │                         #   Problems, Approvals, Service Catalog, KB
│   │   └── web/widget.html
│   └── .env.example
│
├── sap-mcp-app/               # SAP S/4HANA (port 3002)
│   ├── sap_s4hana_mcp/
│   │   ├── sap_server.py         # 14 tools — POs, Business Partners, Materials
│   │   ├── sap_client.py
│   │   └── web/widget.html
│   └── .env.example
│
├── hubspot-mcp-app/           # HubSpot Marketing (port 3003)
│   ├── hubspot_mcp/
│   │   ├── hubspot_server.py     # 29 tools — Emails, Lists, Contacts, Campaigns
│   │   ├── hubspot_client.py
│   │   └── web/widget.html
│   └── .env.example
│
├── flight-mcp-app/            # Flight Tracker (port 3004) — mock-ready
│   ├── flight_mcp/
│   │   ├── flight_server.py      # 5 tools — departures, arrivals, state, track
│   │   └── web/widget.html
│   └── .env.example
│
├── docusign-mcp-app/          # DocuSign eSignature (port 3005) — mock-ready
│   ├── docusign_mcp/
│   │   ├── docusign_server.py    # 9 tools — envelopes, templates, send, void, sign
│   │   └── web/widget.html
│   └── .env.example
│
├── saphr-mcp-app/             # SAP SuccessFactors HR (port 3006) — mock-ready
│   ├── saphr_mcp/
│   │   └── saphr_server.py       # 20 tools — employees, leave, time, performance
│   └── .env.example
│
├── workday-mcp-app/           # Workday HCM (port 3007) — mock-ready
│   ├── workday_mcp/
│   │   └── workday_server.py     # 46 tools — workers, skills, learning, org
│   └── .env.example
│
├── coupa-mcp-app/             # Coupa Procurement (port 3008) — mock-ready
│   ├── coupa_mcp/
│   │   └── coupa_server.py       # 21 tools — requisitions, POs, suppliers, invoices
│   └── .env.example
│
├── jira-mcp-app/              # Jira Projects (port 3009) — mock-ready
│   ├── jira_mcp/
│   │   └── jira_server.py        # 26 tools — issues, sprints, boards, projects
│   └── .env.example
│
├── gateway/                   # ASGI gateway — all 10 LOBs on port 8080
│   ├── app.py                 # Starlette mounts at /sf /sn /sap /hs /ft /ds
│   │                          #   /saphr /workday /coupa /jira
│   └── Dockerfile             # Build context must be project root
│
├── deploy/                    # Azure Container Apps IaC
│   ├── main.bicep             # ACR + Log Analytics + CAE + managed identity
│   │                          #   + gtc-gateway container app
│   ├── deploy.sh              # Provision → az acr build → az containerapp update
│   └── parameters.example.bicepparam
│
├── widgets/                   # React widget source (6 LOBs)
│   ├── src/{lob}/             # index.html, main.tsx, App.tsx, types.ts
│   ├── src/shared/            # McpBridge, FluentWrapper, Toast, ErrorBoundary
│   └── build.mjs              # Vite single-file build → ../web/widget.html
│
├── lob-agent/                 # Enterprise LOB Copilot declarative agent
│   ├── appPackage/
│   │   ├── declarativeAgent.json
│   │   ├── manifest.json
│   │   ├── ai-plugin.json     # 225 functions, 10 runtimes
│   │   ├── mcp-tools.json     # Tool schemas with _meta + widget URIs
│   │   └── instruction.txt
│   └── skills/                # Per-LOB scenario prompts
│
├── docker-compose.yml         # All 10 LOBs (ports 3000–3009) + gateway profile
└── deploy/SetSail.ps1               # One-command startup (Docker + tunnel)
```

---

## Prerequisites

| Requirement | Notes |
|---|---|
| **Docker Desktop** | Latest — recommended for the gateway or individual LOBs |
| Python ≥ 3.11 | Only if running without Docker |
| Node.js ≥ 18 | For widget builds (`cd widgets && npm run build`) |
| M365 Agents Toolkit | VS Code extension or `teamsapp` CLI |
| Dev Tunnels CLI | `devtunnel` — or use Azure Container Apps (no tunnel needed) |
| M365 Developer Tenant | Copilot license + sideloading enabled |

**LOB credentials** (all optional — servers fall back to mock mode without them):

| LOB | Free tier available? |
|-----|---------------------|
| Salesforce | Developer Edition org at developer.salesforce.com |
| ServiceNow | Developer instance at developer.servicenow.com |
| SAP S/4HANA | Free sandbox API key at api.sap.com |
| HubSpot | Free CRM account + Private App token |
| Flight Tracker | Free account at opensky-network.org *(mock works without)* |
| DocuSign | Developer sandbox at developers.docusign.com *(mock works without)* |
| SAP SuccessFactors | SAP BTP trial *(mock works without)* |
| Workday | Workday tenant *(mock works without)* |
| Coupa | Coupa sandbox *(always mock by default)* |
| Jira | Atlassian Cloud free tier *(mock works without)* |

---

## Setup

### 1. Clone & configure credentials

```bash
git clone https://github.com/kaul-vineet/LOB-MCPAppsSample.git
cd lob-mcp-apps
```

Copy `.env.example` → `.env` for each LOB and fill in credentials (leave blank for mock mode):

```bash
cp sf-mcp-app/.env.example       sf-mcp-app/.env
cp snow-mcp-app/.env.example     snow-mcp-app/.env
cp sap-mcp-app/.env.example      sap-mcp-app/.env
cp hubspot-mcp-app/.env.example  hubspot-mcp-app/.env
cp flight-mcp-app/.env.example   flight-mcp-app/.env
cp docusign-mcp-app/.env.example docusign-mcp-app/.env
cp saphr-mcp-app/.env.example    saphr-mcp-app/.env
cp workday-mcp-app/.env.example  workday-mcp-app/.env
cp coupa-mcp-app/.env.example    coupa-mcp-app/.env
cp jira-mcp-app/.env.example     jira-mcp-app/.env
```

### 2. Credential quick-reference

#### 🏛️ Salesforce
| Variable | How to get |
|---|---|
| `SF_INSTANCE_URL` | Your org URL — e.g. `https://myorg.salesforce.com` |
| `SF_CLIENT_ID`, `SF_CLIENT_SECRET` | Setup → App Manager → New Connected App → OAuth2 `client_credentials` |

#### 🎫 ServiceNow
| Variable | How to get |
|---|---|
| `SERVICENOW_INSTANCE` | Instance hostname — e.g. `dev12345` |
| `SERVICENOW_CLIENT_ID/SECRET` | Developer instance → OAuth 2.0 app (`AUTH_MODE=oauth`) |
| `SERVICENOW_USERNAME/PASSWORD` | Basic auth fallback (`AUTH_MODE=basic`) |

#### 📦 SAP S/4HANA
| Variable | How to get |
|---|---|
| `SAP_API_KEY` | Free from [api.sap.com](https://api.sap.com) → Copy API Key. Default `SAP_MODE=sandbox` |

#### 🧡 HubSpot
| Variable | How to get |
|---|---|
| `HUBSPOT_ACCESS_TOKEN` | Settings → Integrations → Private Apps. Scopes: `crm.objects.contacts.read/write` |

#### ✈️ Flight Tracker *(mock-ready)*
| Variable | How to get |
|---|---|
| `OPENSKY_CLIENT_ID/SECRET` | [opensky-network.org](https://opensky-network.org) free account — leave blank for mock |

#### ✒️ DocuSign *(mock-ready)*
| Variable | How to get |
|---|---|
| `DOCUSIGN_INTEGRATION_KEY` | DocuSign Developer → Apps → JWT Grant |
| `DOCUSIGN_USER_ID`, `DOCUSIGN_ACCOUNT_ID` | DocuSign developer account |
| `DOCUSIGN_RSA_PRIVATE_KEY` | `base64 -w0 rsa_key.pem` — base64-encoded PEM |

#### 👤 SAP SuccessFactors HR *(mock-ready)*
| Variable | How to get |
|---|---|
| `SAP_SF_ODATA_URL`, `SAP_SF_TOKEN_URL` | SAP BTP → SuccessFactors API |
| `SAP_SF_COMPANY_ID`, `SAP_SF_CLIENT_ID` | SAP BTP service instance credentials |

#### 💼 Workday *(mock-ready)*
| Variable | How to get |
|---|---|
| `WORKDAY_BASE_URL`, `WORKDAY_TENANT` | Workday tenant URL |

#### 🛒 Coupa *(always mock by default)*
| Variable | How to get |
|---|---|
| `COUPA_INSTANCE_URL` | `https://your-org.coupahost.com` — set `COUPA_MOCK=false` for live |

#### 📋 Jira *(mock-ready)*
| Variable | How to get |
|---|---|
| `JIRA_BASE_URL` | `https://your-org.atlassian.net` |
| `JIRA_PROJECT_KEY` | e.g. `GTC` |

### 3. Dev Tunnel (one-time, local dev only)

```bash
devtunnel user login -d
devtunnel create gtc-tunnel --allow-anonymous
devtunnel port create gtc-tunnel -p 8080    # Gateway (recommended — single port)
# Or individual LOB ports if using docker-compose without gateway:
devtunnel port create gtc-tunnel -p 3000    # Salesforce
devtunnel port create gtc-tunnel -p 3001    # ServiceNow
# ... repeat for 3002–3009
```

Update `lob-agent/appPackage/ai-plugin.json` runtime URLs with your tunnel hostname, or run `python regen_manifests.py` after setting `MCP_GATEWAY_URL`.

### 4. Agent provisioning

```bash
cd lob-agent
teamsapp auth login m365
teamsapp provision --env dev
```

Or via ATK sidebar in VS Code: **Lifecycle → Provision**.

---

## Running

### Option A: ASGI Gateway (Recommended) ⚡

All 10 LOBs in one process on port 8080. This is the mode used with Azure Container Apps and the standard dev tunnel setup.

```bash
# Docker (build context = project root)
docker compose --profile gateway up gateway

# Or run locally
pip install -e ./shared-mcp-lib -e ./gateway  # plus all 10 LOB packages
python -m gateway

# Tunnel
devtunnel host gtc-tunnel --allow-anonymous
```

Routes: `/sf/mcp` `/sn/mcp` `/sap/mcp` `/hs/mcp` `/ft/mcp` `/ds/mcp` `/saphr/mcp` `/workday/mcp` `/coupa/mcp` `/jira/mcp`

### Option B: Docker Compose 🐳

Individual containers per LOB (ports 3000–3009):

```bash
docker compose up -d                          # all 10 LOBs
docker compose up salesforce servicenow sap   # specific LOBs only
devtunnel host gtc-tunnel --allow-anonymous

docker compose ps
docker compose logs -f
docker compose down
```

### Option C: Python Venvs (dev)

```bash
# Install shared lib first
pip install -e ./shared-mcp-lib

# Then each LOB
pip install -e ./sf-mcp-app    && python -m sf_crm_mcp         # :3000
pip install -e ./snow-mcp-app  && python -m servicenow_mcp     # :3001
pip install -e ./sap-mcp-app   && python -m sap_s4hana_mcp     # :3002
pip install -e ./hubspot-mcp-app && python -m hubspot_mcp      # :3003
pip install -e ./flight-mcp-app  && python -m flight_mcp       # :3004
pip install -e ./docusign-mcp-app && python -m docusign_mcp    # :3005
pip install -e ./saphr-mcp-app   && python -m saphr_mcp        # :3006
pip install -e ./workday-mcp-app && python -m workday_mcp      # :3007
pip install -e ./coupa-mcp-app   && python -m coupa_mcp        # :3008
pip install -e ./jira-mcp-app    && python -m jira_mcp         # :3009
```

---

## Deploy to Azure

Deploy the gateway to Azure Container Apps — no dev tunnel needed, stable Azure FQDN.

### Prerequisites

```bash
az login
az account set -s <subscription-id>
az bicep install
```

### Deploy

```bash
cp deploy/parameters.example.bicepparam deploy/parameters.bicepparam
# Edit parameters.bicepparam with real credentials (this file is .gitignored)

export RESOURCE_GROUP=gtc-rg
export LOCATION=eastus
export ACR_NAME=gtcregistry   # must be globally unique

bash deploy/deploy.sh
```

The script:
1. Creates the resource group
2. Deploys `deploy/main.bicep` — ACR, Log Analytics, Container Apps environment, managed identity, and the `gtc-gateway` container app (external ingress, port 8080)
3. Builds all 11 images in ACR using `az acr build` (remote build — no Docker daemon needed locally)
4. Updates the container app with the new images

### After deploy — update the manifest URL

```bash
export MCP_GATEWAY_URL=https://<your-gateway-fqdn>
python regen_manifests.py
```

Then re-provision the Teams agent with the new URLs.

### Bicep resources created

| Resource | SKU / Notes |
|---|---|
| Azure Container Registry | Basic |
| Log Analytics Workspace | PerGB2018, 30-day retention |
| Container Apps Environment | Consumption plan |
| User-Assigned Managed Identity | AcrPull on the registry |
| `gtc-gateway` Container App | 1–3 replicas, external ingress, 1 vCPU / 2 GiB |

---

## Mock Mode

All six original LOBs (Flight, DocuSign) plus all four new LOBs (SAP HR, Workday, Coupa, Jira) support mock mode — realistic demo data with no real credentials needed.

| LOB | Mock triggers | Mock data |
|-----|--------------|-----------|
| Flight Tracker | `OPENSKY_CLIENT_ID` absent | 5 GTC-themed flights (Dubai→London, etc.) with live-style positions |
| DocuSign | Credentials absent | 5 mock envelopes (NDA, MSA, Cargo contract…), 4 templates |
| SAP SuccessFactors HR | `SAP_SF_ODATA_URL` absent | 5 mock employees, leave balances, org chart |
| Workday | `WORKDAY_BASE_URL` absent | Mock workers, skills, learning completions |
| Coupa | `COUPA_MOCK=true` (default) | Mock requisitions, POs, supplier list |
| Jira | `JIRA_BASE_URL` absent | Mock issues, sprint board, project list |

Mock mode activates automatically — the agent and widget see identical response shapes as with live credentials.

---

## Static Analysis — check_meta.py

Validates tool definitions stay in sync across all three sources of truth:

```bash
python check_meta.py              # exits 1 if drift detected
python check_meta.py --verbose    # full per-tool report
```

| Check | What it verifies |
|-------|-----------------|
| `_meta` presence | Every tool in `mcp-tools.json` has `_meta.ui.resourceUri` |
| Plugin registration | Every manifest tool appears in `ai-plugin.json` |
| Server drift | Tools in `server.py` match `mcp-tools.json` |

> The four new LOBs (saphr, workday, coupa, jira) use programmatic tool registration (`mcp.tool(...)()` loop pattern). Check 3 will warn "no `@mcp.tool` decorators found" for these — this is expected. Checks 1 and 2 still pass and verify all 225 tools are correctly manifested.

---

## Manifest Generation — regen_manifests.py

Regenerates `mcp-tools.json` and `ai-plugin.json` by importing all 10 server modules and reading their live tool registrations.

```bash
# Local dev (devtunnel URL)
python regen_manifests.py

# After Azure deployment — point at your Container Apps FQDN
MCP_GATEWAY_URL=https://<your-gateway-fqdn> python regen_manifests.py
```

Run after adding or renaming tools, then re-provision the agent.

---

## Skills System

`lob-agent/skills/` documents per-LOB scenario prompts used as conversation starters:

| File | LOB | Example starter |
|------|-----|----------------|
| `crm-pipeline.md` | Salesforce | *"Show me the latest leads. I want to review qualified ones."* |
| `incident-triage.md` | ServiceNow | *"Show me open incidents sorted by priority."* |
| `procurement-check.md` | SAP | *"Show me recent purchase orders."* |
| `campaign-performance.md` | HubSpot | *"Which campaigns have the best open rates?"* |
| `flight-tracker.md` | Flight | *"Show me departures from Heathrow today."* |
| `docusign-envelopes.md` | DocuSign | *"Show me envelopes awaiting signature."* |
| `cross-lob-operations.md` | All LOBs | *"Give me an end-of-day operations check."* |

---

## Tools Reference

### 🏛️ Salesforce CRM — 31 tools (port 3000)

| Tool | Description |
|---|---|
| `sf__get_leads` | Latest 5 leads |
| `sf__create_lead` | Create lead |
| `sf__update_lead` | Update lead |
| `sf__delete_lead` | Delete lead |
| `sf__convert_lead` | Convert lead → Account + Contact + Opportunity |
| `sf__get_opportunities` | Latest 5 opportunities |
| `sf__create_opportunity` | Create opportunity |
| `sf__update_opportunity` | Update opportunity |
| `sf__get_accounts` | Latest 5 accounts |
| `sf__create_account` | Create account |
| `sf__update_account` | Update account |
| `sf__get_contacts` | Latest 5 contacts |
| `sf__create_contact` | Create contact |
| `sf__update_contact` | Update contact |
| `sf__get_cases` | Latest 5 cases |
| `sf__create_case` | Create case |
| `sf__update_case` | Update case status/resolution |
| `sf__get_tasks` | Latest 5 tasks/activities |
| `sf__create_task` | Create task |
| `sf__get_pipeline_dashboard` | Opportunity pipeline by stage (count + amount) |
| `sf__get_campaigns` | Latest 5 campaigns |
| `sf__get_pending_approvals` | Pending ProcessInstance workitems |
| `sf__get_products` | Product catalog |
| `sf__get_price_books` | Price books |
| `sf__get_quotes` | Recent quotes |
| `sf__create_quote` | Create quote from opportunity |
| `sf__get_contracts` | Active contracts |
| `sf__get_activities_timeline` | Activity history for a record |

> Full list: see `sf_crm_mcp/salesforce_server.py` → `TOOL_SPECS`

### 🎫 ServiceNow ITSM — 24 tools (port 3001)

| Tool | Description |
|---|---|
| `sn__get_incidents` | Latest incidents |
| `sn__create_incident` | Create incident |
| `sn__update_incident` | Update incident |
| `sn__resolve_incident` | Resolve/close incident |
| `sn__get_requests` | Latest service requests |
| `sn__create_request` | Create request |
| `sn__update_request` | Update request |
| `sn__get_request_items` | Items for a request |
| `sn__update_request_item` | Update request item |
| `sn__get_change_requests` | Latest change requests |
| `sn__create_change_request` | Create change request |
| `sn__get_problems` | Latest problem records |
| `sn__get_pending_approvals` | Pending approvals queue |
| `sn__get_service_catalog_items` | Active catalog items |
| `sn__add_work_note` | Add work note to a record |
| `sn__get_knowledge_articles` | Knowledge base search |
| `sn__create_incident_form` | Open incident creation form widget |
| `sn__create_request_form` | Open request creation form widget |
| `sn__approve_request` | Approve a pending approval |
| `sn__reject_request` | Reject a pending approval |
| `sn__get_user_profile` | User profile lookup |
| `sn__get_cmdb_ci` | Configuration item from CMDB |
| `sn__get_sla_details` | SLA metrics for an incident |
| `sn__update_change_request` | Update change request |

> Full list: see `servicenow_mcp/servicenow_server.py` → `TOOL_SPECS`

### 📦 SAP S/4HANA — 14 tools (port 3002)

| Tool | Description |
|---|---|
| `sap__get_purchase_orders` | Latest purchase orders |
| `sap__get_business_partners` | Business partners / suppliers |
| `sap__get_materials` | Materials master data |
| `sap__create_purchase_order` | Create PO (mock ID in sandbox) |
| `sap__update_purchase_order` | Update PO |
| `sap__get_material_details` | Material detail by ID |
| `sap__get_sales_orders` | Sales orders list |
| `sap__get_invoices` | Accounts payable invoices |
| `sap__get_goods_receipts` | Goods receipts for a PO |
| `sap__get_cost_centers` | Cost center master data |
| `sap__get_gl_accounts` | G/L account master data |
| `sap__get_profit_centers` | Profit center list |
| `sap__approve_purchase_order` | Approve / reject a PO workflow |
| `sap__get_stock_overview` | Material stock levels |

### 🧡 HubSpot Marketing — 29 tools (port 3003)

| Tool | Description |
|---|---|
| `hs__get_emails` | Marketing emails with metrics |
| `hs__get_lists` | Contact lists / segments |
| `hs__get_list_contacts` | Contacts in a list |
| `hs__add_to_list` | Add contact to list |
| `hs__remove_from_list` | Remove contact from list |
| `hs__update_email` | Edit email name/subject |
| `hs__update_list` | Edit list name |
| `hs__create_contact` | Create contact |
| `hs__get_contacts` | Recent contacts |
| `hs__update_contact` | Update contact |
| `hs__get_deals` | Recent deals |
| `hs__create_deal` | Create deal |
| `hs__get_companies` | Recent companies |
| `hs__create_company` | Create company |
| `hs__get_campaigns` | Marketing campaigns |
| `hs__get_campaign_metrics` | Opens, clicks, conversions per campaign |
| `hs__clone_email` | Clone a marketing email |
| `hs__send_test_email` | Send test email to an address |
| `hs__get_forms` | Landing page forms |
| `hs__get_form_submissions` | Form submission entries |
| `hs__get_workflows` | Active automation workflows |
| `hs__enroll_in_workflow` | Enroll a contact in a workflow |
| `hs__get_tickets` | Support tickets |
| `hs__create_ticket` | Create support ticket |
| `hs__update_ticket` | Update ticket status/owner |
| `hs__get_owners` | HubSpot users / owners |
| `hs__get_pipelines` | Deal pipelines |
| `hs__update_deal` | Update deal stage/amount |
| `hs__delete_contact` | Delete a contact |

> Full list: see `hubspot_mcp/hubspot_server.py` → `TOOL_SPECS`

### ✈️ Flight Tracker — 5 tools (port 3004)

| Tool | Description |
|---|---|
| `ft__get_airport_departures` | Departures from ICAO airport |
| `ft__get_airport_arrivals` | Arrivals at ICAO airport |
| `ft__get_aircraft_state` | Live position/speed/altitude |
| `ft__get_flights_by_aircraft` | Flight history for aircraft |
| `ft__get_aircraft_track` | Waypoints for a flight |

### ✒️ DocuSign eSignature — 9 tools (port 3005)

| Tool | Description |
|---|---|
| `ds__get_envelopes` | List envelopes with status filters |
| `ds__get_envelope_details` | Recipient and signing progress |
| `ds__get_templates` | Available signing templates |
| `ds__send_envelope` | Send envelope from template |
| `ds__void_envelope` | Void / cancel an envelope |
| `ds__resend_envelope` | Resend to pending signers |
| `ds__get_signing_url` | Generate embedded signing URL |
| `ds__download_document` | Download signed document |
| `ds__send_envelope_form` | Open send-envelope form widget |

### 👤 SAP SuccessFactors HR — 20 tools (port 3006)

Employee self-service: profile, leave balances, time-off requests, org chart, performance goals, learning, benefits, and more.

### 💼 Workday HCM — 46 tools (port 3007)

Worker context, skills, required learning, org chart, absence management, compensation, and more.

### 🛒 Coupa Procurement — 21 tools (port 3008)

Requisitions, purchase orders, suppliers, invoices, budgets, approval workflows, and more.

### 📋 Jira Projects — 26 tools (port 3009)

Issues (CRUD), sprints, boards, projects, epics, comments, attachments, transitions, and more.

---

## Widget Architecture

React 19 + Fluent UI v9 widgets compiled into single-file HTML via Vite + `vite-plugin-singlefile`. Six of the ten LOBs have live widgets; four (SAP HR, Workday, Coupa, Jira) are in progress.

| Widget | Design System | Key Visual Elements |
|--------|--------------|-------------------|
| **Salesforce** | Lightning SLDS | Blue header, pill status badges, compact CRUD forms |
| **SAP** | Fiori | Shell bar, '72' font, Object Page layout |
| **HubSpot** | Canvas | Metric cards, percentage bars, coral/teal palette, 3-level drill-down |
| **ServiceNow** | Now Design | Teal shell, P1–P4 priority colors |
| **Flight Tracker** | Fluent v9 | Dark sky theme, live status badges, altitude/speed metrics |
| **DocuSign** | DocuSign brand | Envelope status cards, signer progress |

### Platform features

| Feature | Implementation |
|---------|---------------|
| MCP Apps protocol | `@modelcontextprotocol/ext-apps` — handshake + tool-result delivery |
| Side-by-side mode | `app.requestDisplayMode('fullscreen')` |
| Auto theming | Light/dark via host context |
| Skeleton loading | CSS shimmer while data loads |
| Error boundaries | Crash recovery UI with "Try Again" |
| CRUD operations | Create/read/update across all 6 live LOBs |
| Toast notifications | Success/error after save |

### Building widgets

```bash
cd widgets
npm install
npm run build          # all 6 widgets
npm run build:sf       # specific LOB
```

Output: `widgets/dist/{lob}.html` → copied to `{lob}-mcp-app/{pkg}/web/widget.html`.

---

## Logs & Monitoring

### Container logs (stdout)

```bash
# Gateway mode
docker compose --profile gateway logs -f gateway

# Individual LOBs
docker compose logs -f salesforce   # :3000
docker compose logs -f servicenow   # :3001
docker compose logs -f sap          # :3002
docker compose logs -f hubspot      # :3003
docker compose logs -f flight       # :3004
docker compose logs -f docusign     # :3005
docker compose logs -f saphr        # :3006
docker compose logs -f workday      # :3007
docker compose logs -f coupa        # :3008
docker compose logs -f jira         # :3009
```

For structured telemetry — tool latencies, success rates, and record counts by LOB — see the [Telemetry — App Insights](#telemetry--app-insights) section below.

---

## Telemetry — App Insights

Every tool call is automatically instrumented via `shared_mcp/telemetry.py`. Each invocation fires a `dependency` event to Azure Application Insights — without blocking the tool response.

### What is captured per tool call

| Field | Description |
|---|---|
| `name` | Tool name (e.g. `sf__get_leads`) |
| `target` | LOB label (e.g. `salesforce-crm`) |
| `duration` | Wall-clock time in milliseconds |
| `success` | `true` / `false` |
| `resultType` | Value of `structuredContent.type` (e.g. `leads`, `incidents`) |
| `recordCount` | Value of `structuredContent.total` |
| `error` | Error message if the tool threw or returned an error |
| `cloud_RoleName` | Deployment name (env var) — useful in multi-agent environments |
| `cloud_RoleInstance` | Derived from the tool name prefix (sf, sn, sap, hs, ft, ds, saphr, wday, coupa, jira) |

### Setup

**Step 1 — Get your App Insights connection string**

Azure Portal → Application Insights resource → Overview → **Connection String** (copy the full string).

**Step 2 — Add to each `.env` file (or gateway environment)**

```env
APPINSIGHTS_CONNECTION_STRING=InstrumentationKey=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx;IngestionEndpoint=https://eastus.in.applicationinsights.azure.com/
APPINSIGHTS_ROLE_NAME=lob-mcp
```

Leave `APPINSIGHTS_CONNECTION_STRING` blank (or omit it) to disable telemetry entirely — zero overhead, no HTTP calls made.

**Step 3 — In `docker-compose.yml` gateway block (already wired)**

```yaml
environment:
  GATEWAY_PORT: "8080"
  APPINSIGHTS_CONNECTION_STRING: ""   # paste connection string to activate
  APPINSIGHTS_ROLE_NAME: "lob-mcp"
```

### Viewing telemetry in App Insights

**Transactions view** — App Insights → Transaction Search → filter by `dependency`

**KQL — all tool calls in the last hour**

```kql
dependencies
| where timestamp > ago(1h)
| where type == "MCP Tool"
| project timestamp, name, target, duration, success, resultCode
| order by timestamp desc
```

**KQL — slowest tools**

```kql
dependencies
| where type == "MCP Tool"
| summarize avg(duration), percentile(duration, 95), count() by name
| order by avg_duration desc
```

**KQL — failure rate by LOB**

```kql
dependencies
| where type == "MCP Tool"
| summarize total=count(), failures=countif(success == false) by target
| extend failure_pct = round(100.0 * failures / total, 1)
| order by failure_pct desc
```

**KQL — record volume trend (e.g. leads returned)**

```kql
dependencies
| where type == "MCP Tool" and name startswith "sf__"
| extend recordCount = toint(customDimensions["resultCount"])
| summarize total_records=sum(recordCount) by bin(timestamp, 1h)
| render timechart
```

### Application Map

With `cloud_RoleInstance` set per LOB prefix, App Insights **Application Map** automatically draws one node per LOB showing call rates and failure percentages. Navigate to Application Insights → Application Map.

### Multi-agent environments

If the same MCP servers are shared across multiple agents, set a distinct `APPINSIGHTS_ROLE_NAME` per deployment (e.g. `lob-mcp-prod`, `lob-mcp-uat`). Query by `cloud_RoleName` to isolate traffic per agent.

---

## Critical Troubleshooting

1. **MCP Apps handshake** — Widget must send `ui/initialize` → wait for host response → send `ui/notifications/initialized`. Only then will the host deliver `ui/notifications/tool-result`.

2. **`--allow-anonymous` on the tunnel** — Required on both `devtunnel create` and `devtunnel host`. Without it, M365 Copilot's backend can't reach your MCP endpoints.

3. **`_meta` placement** — `_meta.ui.resourceUri` must be on the tool definition in `mcp-tools.json`, **not** inside `inputSchema`.

4. **Manifest drift** — Run `python check_meta.py` after adding tools. Run `python regen_manifests.py` to regenerate manifests.

5. **`callTool` method** — Widget-to-host calls must use `method: 'tools/call'` with `arguments` (not `ui/callTool` with `args`).

6. **Custom App Upload Enabled** — ATK sidebar → Accounts. Both "Custom App Upload Enabled ✓" and "Copilot Access Enabled ✓" must show.

7. **Gateway URL** — After Azure deployment, update `MCP_GATEWAY_URL` and re-run `regen_manifests.py`, then re-provision the agent.

8. **New LOBs returning mock data** — Expected when credentials aren't configured. Set the relevant env vars and restart to use live APIs.

---

## Adding a New LOB

1. Copy an app folder (e.g. `flight-mcp-app/`) and rename the Python package
2. Replace the API client with your LOB's auth + REST calls
3. Keep `@mcp.tool(meta={"ui": {"resourceUri": WIDGET_URI}})` and `types.CallToolResult` with `structuredContent` returns
4. Add the new app to `gateway/app.py` (Mount) and `gateway/Dockerfile` (COPY + pip install)
5. Add a service to `docker-compose.yml`
6. Add a Bicep `containerApp` resource (or update `deploy/main.bicep`)
7. Run `python regen_manifests.py` → `python check_meta.py`
8. Re-provision the agent

---

## References

- [MCP Apps in M365 Copilot](https://learn.microsoft.com/microsoft-365-copilot/extensibility/mcp-apps-overview)
- [FastMCP SDK](https://github.com/jlowin/fastmcp)
- [M365 Agents Toolkit](https://learn.microsoft.com/microsoftteams/platform/toolkit/teams-toolkit-fundamentals)
- [Dev Tunnels Documentation](https://learn.microsoft.com/azure/developer/dev-tunnels/overview)
- [Azure Container Apps](https://learn.microsoft.com/azure/container-apps/)
- [Salesforce REST API](https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/)
- [ServiceNow Table API](https://docs.servicenow.com/bundle/latest/page/integrate/inbound-rest/concept/c_TableAPI.html)
- [SAP Business Hub API](https://api.sap.com)
- [OpenSky Network API](https://openskynetwork.github.io/opensky-api/)
- [DocuSign eSignature REST API](https://developers.docusign.com/docs/esign-rest-api/)
- [Jira REST API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
