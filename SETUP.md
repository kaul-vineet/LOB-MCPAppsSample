# The Great Trading Company — Detailed Setup Guide

> **Audience:** This guide assumes no prior experience with Salesforce, ServiceNow, SAP, or HubSpot APIs. It walks you through getting free developer accounts, obtaining credentials, and running each MCP app step by step.

---

## Table of Contents

1. [Prerequisites (install once)](#1-prerequisites-install-once)
2. [Salesforce CRM — Getting Your Credentials](#2-salesforce-crm--getting-your-credentials)
3. [ServiceNow — Getting Your Credentials](#3-servicenow--getting-your-credentials)
4. [SAP S/4HANA — Getting Your API Key](#4-sap-s4hana--getting-your-api-key)
5. [HubSpot CRM — Getting Your Access Token](#5-hubspot-crm--getting-your-access-token)
6. [Setting Up the Dev Tunnel](#6-setting-up-the-dev-tunnel)
7. [Installing & Running Each MCP App](#7-installing--running-each-mcp-app)
8. [Deploying the Agent to M365 Copilot](#8-deploying-the-agent-to-m365-copilot)
9. [Verifying Everything Works](#9-verifying-everything-works)
10. [Authentication Deep Dive](#10-authentication-deep-dive)

---

## 1. Prerequisites (install once)

Before you begin, install these tools on your machine:

| Tool | What it does | How to install |
|---|---|---|
| **Python 3.11+** | Runs the MCP servers | [python.org/downloads](https://www.python.org/downloads/) — check "Add to PATH" during install |
| **Node.js 18+** | Required by the Teams Toolkit CLI | [nodejs.org](https://nodejs.org/) — use the LTS version |
| **Git** | Version control | [git-scm.com](https://git-scm.com/downloads) |
| **VS Code** | Code editor | [code.visualstudio.com](https://code.visualstudio.com/) |
| **M365 Agents Toolkit** | VS Code extension for deploying the agent | Search "Teams Toolkit" in VS Code Extensions marketplace |
| **Dev Tunnels CLI** | Exposes your local servers to the internet | [Install guide](https://learn.microsoft.com/azure/developer/dev-tunnels/get-started) |

**Verify your installs** — open a terminal and run:
```bash
python --version     # Should show 3.11 or higher
node --version       # Should show 18 or higher
git --version        # Any version is fine
devtunnel --version  # Any version is fine
```

---

## 2. Salesforce CRM — Getting Your Credentials

You need three values: `SF_INSTANCE_URL`, `SF_CLIENT_ID`, `SF_CLIENT_SECRET`.

### Step 1: Get a free Salesforce Developer Org

1. Go to [developer.salesforce.com/signup](https://developer.salesforce.com/signup)
2. Fill in the form — use your real email (you'll need to verify it)
3. Click **Sign me up**
4. Check your email → click the verification link → set your password
5. You're now logged into your Salesforce org

> 💡 Your instance URL looks like `https://your-name-dev-ed.develop.my.salesforce.com`. Copy it — that's your `SF_INSTANCE_URL`.

### Step 2: Create a Connected App

1. In Salesforce, click the **gear icon** (top right) → **Setup**
2. In the left search box (Quick Find), type **App Manager** → click it
3. Click **New Connected App** (top right)
4. Fill in:
   - **Connected App Name:** `MCP Integration`
   - **API Name:** auto-fills
   - **Contact Email:** your email
5. Scroll down → check ✅ **Enable OAuth Settings**
   - **Callback URL:** `https://localhost` (we won't use this, but it's required)
   - **Selected OAuth Scopes:** add `Access and manage your data (api)`
   - Check ✅ **Enable Client Credentials Flow**
6. Click **Save** → then **Continue**

### Step 3: Copy your Client ID and Secret

1. After saving, you'll see the app details page
2. Click **Manage Consumer Details** (you may need to verify via email code)
3. Copy the **Consumer Key** → this is your `SF_CLIENT_ID`
4. Copy the **Consumer Secret** → this is your `SF_CLIENT_SECRET`

### Step 4: Set the Run-As User

1. Go back to **App Manager** → find your app → click the dropdown (**▼**) → **Manage**
2. Click **Edit Policies**
3. Under **Client Credentials Flow**, set the **Run As** user to your admin user
4. Click **Save**

### Step 5: Fill in your .env file

```bash
cd sf-mcp-app
copy .env.example .env
```

Edit `.env`:
```
SF_INSTANCE_URL=https://your-name-dev-ed.develop.my.salesforce.com
SF_CLIENT_ID=your-consumer-key-here
SF_CLIENT_SECRET=your-consumer-secret-here
PORT=3000
CORS_ORIGINS=*
```

---

## 3. ServiceNow — Getting Your Credentials

You need: `SERVICENOW_INSTANCE`, `SERVICENOW_CLIENT_ID`, `SERVICENOW_CLIENT_SECRET` (for OAuth) or `SERVICENOW_USERNAME`, `SERVICENOW_PASSWORD` (for Basic Auth).

### Step 1: Get a free Personal Developer Instance (PDI)

1. Go to [developer.servicenow.com](https://developer.servicenow.com/)
2. Click **Sign Up** → create an account with your email
3. Once logged in, click **Request Instance** from the dashboard
4. Choose the latest release (e.g., Zurich or Washington)
5. Wait ~2 minutes → your instance is ready
6. Note your **Instance URL** — it looks like `https://dev12345.service-now.com`
7. Your instance name (just `dev12345`) is your `SERVICENOW_INSTANCE`

> 💡 Your admin credentials are shown on the dashboard (usually `admin` / a generated password). Save them!

### Option A: Basic Auth (simplest — recommended for getting started)

Just use the admin username and password. Edit your `.env`:

```
SERVICENOW_INSTANCE=dev12345
SERVICENOW_AUTH_MODE=basic
SERVICENOW_USERNAME=admin
SERVICENOW_PASSWORD=your-generated-password
```

### Option B: OAuth (more secure — recommended for demos)

#### Step 2: Enable Client Credentials Grant

1. In your ServiceNow instance, go to **System Properties** → search for `glide.oauth.inbound.client.credential.grant_type.enabled`
2. Set the value to `true` → **Save**

#### Step 3: Create an OAuth Application

1. Navigate to **System OAuth** → **Application Registry**
2. Click **New**
3. Select **Create an OAuth API endpoint for external clients**
4. Fill in:
   - **Name:** `MCP Integration`
   - Leave Client ID and Secret as auto-generated (or set your own)
5. Click **Submit**
6. Open the record you just created → copy the **Client ID** and **Client Secret**

#### Step 4: Fill in your .env file

```bash
cd snow-mcp-app
copy .env.example .env
```

Edit `.env`:
```
SERVICENOW_INSTANCE=dev12345
SERVICENOW_AUTH_MODE=oauth
SERVICENOW_CLIENT_ID=your-client-id
SERVICENOW_CLIENT_SECRET=your-client-secret
PORT=3001
CORS_ORIGINS=*
```

---

## 4. SAP S/4HANA — Getting Your API Key

You need: `SAP_API_KEY`. This connects to the free API Business Hub sandbox (read-only).

### Step 1: Create a free SAP account

1. Go to [api.sap.com](https://api.sap.com)
2. Click **Log On** (top right)
3. If you don't have an account, click **Register** → fill in the form → verify your email
4. Log in

### Step 2: Get your API Key

1. Once logged in, click your **profile icon** (top right) → **Settings**
2. You'll see a section called **API Key** or look under your profile/credentials
3. If you see a **Show API Key** button → click it → copy the key
4. If no key exists, click **Generate API Key** → copy it

> 💡 This is a free key that works with all sandbox APIs on api.sap.com. No credit card needed.

### Step 3: Verify it works (optional)

1. On [api.sap.com](https://api.sap.com), search for **Purchase Order** → select **Purchase Order (A2X)**
2. Click **Try Out** → select the **GET** endpoint for `/A_PurchaseOrder`
3. Your API key should auto-fill → click **Execute**
4. You should see sample purchase order data in the response

### Step 4: Fill in your .env file

```bash
cd sap-mcp-app
copy .env.example .env
```

Edit `.env`:
```
SAP_MODE=sandbox
SAP_API_KEY=your-api-key-from-api-sap-com
PORT=3002
CORS_ORIGINS=*
```

> 📡 In sandbox mode, you can only **read** data. Create and update operations return mock demo data. This is perfect for demos and development.

---

## 5. HubSpot CRM — Getting Your Access Token

You need: `HUBSPOT_ACCESS_TOKEN`.

### Step 1: Create a free HubSpot account

1. Go to [app.hubspot.com/signup](https://app.hubspot.com/signup-hubspot/crm)
2. Choose **Get started free** → sign up with your email
3. Follow the onboarding wizard (you can skip most steps)
4. You now have a free HubSpot CRM with full API access

### Step 2: Create a Private App

1. In HubSpot, click the **⚙️ Settings** gear icon (top right)
2. In the left sidebar, navigate to **Integrations** → **Private Apps**
3. Click **Create a private app**
4. Fill in:
   - **App name:** `MCP Integration`
   - **Description:** (optional) `MCP server for M365 Copilot`

### Step 3: Set Permissions (Scopes)

1. Click the **Scopes** tab
2. Search for and enable these scopes:
   - ✅ `crm.objects.contacts.read`
   - ✅ `crm.objects.contacts.write`
   - ✅ `crm.objects.deals.read`
   - ✅ `crm.objects.deals.write`
3. Click **Update** to save the scopes

### Step 4: Generate the Token

1. Click **Create app** (top right)
2. A confirmation dialog appears → click **Continue creating**
3. Your **access token** appears in a green box at the top of the page
4. ⚠️ **Copy it immediately!** — it's only shown once. Store it somewhere safe.

> If you lose the token, go back to the Private App → click **Rotate token** to generate a new one.

### Step 5: Fill in your .env file

```bash
cd hubspot-mcp-app
copy .env.example .env
```

Edit `.env`:
```
HUBSPOT_ACCESS_TOKEN=pat-na1-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
PORT=3003
CORS_ORIGINS=*
```

---

## 6. Setting Up the Dev Tunnel

The dev tunnel makes your local MCP servers accessible to M365 Copilot over the internet.

### First-time setup (do this once)

```bash
# Log in to Dev Tunnels (uses your Microsoft account)
devtunnel user login

# Create a persistent named tunnel
devtunnel create gtc-tunnel --allow-anonymous

# Add all four ports
devtunnel port create gtc-tunnel -p 3000
devtunnel port create gtc-tunnel -p 3001
devtunnel port create gtc-tunnel -p 3002
devtunnel port create gtc-tunnel -p 3003
```

### Update ai-plugin.json with your tunnel URLs

After creating the tunnel, check the URLs:
```bash
devtunnel show gtc-tunnel
```

The URLs will look like:
- `https://XXXXX-3000.inc1.devtunnels.ms`
- `https://XXXXX-3001.inc1.devtunnels.ms`
- `https://XXXXX-3002.inc1.devtunnels.ms`
- `https://XXXXX-3003.inc1.devtunnels.ms`

Edit `lob-agent/appPackage/ai-plugin.json` and replace the four tunnel URLs with your actual URLs.

### Starting the tunnel (every dev session)

```bash
devtunnel host gtc-tunnel
```

> 💡 The tunnel name is **persistent** — the URLs stay the same every time you restart. Just don't run `devtunnel delete`. Tunnels expire after 30 days of inactivity.

---

## 7. Installing & Running Each MCP App

### Install all four apps (one time)

Open a terminal in the project root and run:

```bash
# Salesforce
cd sf-mcp-app
python -m venv .venv
.venv\Scripts\activate
pip install -e .
deactivate
cd ..

# ServiceNow
cd snow-mcp-app
python -m venv .venv
.venv\Scripts\activate
pip install -e .
deactivate
cd ..

# SAP
cd sap-mcp-app
python -m venv .venv
.venv\Scripts\activate
pip install -e .
deactivate
cd ..

# HubSpot
cd hubspot-mcp-app
python -m venv .venv
.venv\Scripts\activate
pip install -e .
deactivate
cd ..
```

### Run all four servers (every dev session)

Open **five** terminals:

| Terminal | Commands |
|---|---|
| **Terminal 1 — Salesforce** | `cd sf-mcp-app` → `.venv\Scripts\activate` → `python -m sf_crm_mcp` |
| **Terminal 2 — ServiceNow** | `cd snow-mcp-app` → `.venv\Scripts\activate` → `python -m servicenow_mcp` |
| **Terminal 3 — SAP** | `cd sap-mcp-app` → `.venv\Scripts\activate` → `python -m sap_s4hana_mcp` |
| **Terminal 4 — HubSpot** | `cd hubspot-mcp-app` → `.venv\Scripts\activate` → `python -m hubspot_mcp` |
| **Terminal 5 — Tunnel** | `devtunnel host gtc-tunnel` |

> 💡 **Tip:** You can use VS Code's split terminal feature to see all five at once.

You should see output like:
```
INFO:     Uvicorn running on http://0.0.0.0:3000  (Salesforce)
INFO:     Uvicorn running on http://0.0.0.0:3001  (ServiceNow)
INFO:     Uvicorn running on http://0.0.0.0:3002  (SAP)
INFO:     Uvicorn running on http://0.0.0.0:3003  (HubSpot)
```

---

## 8. Deploying the Agent to M365 Copilot

### Step 1: Provision the agent

```bash
cd lob-agent
teamsapp provision --env dev
```

This registers "The Great Trading Company" as an app in your M365 tenant.

### Step 2: Open M365 Copilot

1. Go to [m365.cloud.microsoft/chat](https://m365.cloud.microsoft/chat) in your browser
2. Click the **agent icon** in the right sidebar (🤖 or the plug icon)
3. Find **The Great Trading Co.** in the list → click it

### Step 3: Start chatting!

Try these prompts:
- 📋 *"Show me the latest leads"* → Salesforce widget appears
- 🎫 *"Show me the latest incidents"* → ServiceNow widget appears
- 📦 *"Show me the latest purchase orders"* → SAP widget appears
- 📇 *"Show me the marketing email performance"* → HubSpot widget appears

---

## 9. Verifying Everything Works

### Quick health check (before deploying the agent)

With all servers running, open a browser or use curl:

```bash
curl http://localhost:3000/mcp    # Salesforce — should return MCP response
curl http://localhost:3001/mcp    # ServiceNow
curl http://localhost:3002/mcp    # SAP
curl http://localhost:3003/mcp    # HubSpot
```

### Widget test (without M365 Copilot)

Each app has standalone test HTML files. Open them in a browser:

- `sf-mcp-app/tests/widget_test.html` — tests the Salesforce widget with mock data
- `snow-mcp-app/tests/widget_test.html` — tests the ServiceNow widget
- `sap-mcp-app/tests/widget_test.html` — tests the SAP widget
- `hubspot-mcp-app/tests/widget_test.html` — tests the HubSpot widget

These let you see and interact with the widgets without needing M365 Copilot.

### Common issues

| Problem | Solution |
|---|---|
| "Module not found" when running | Make sure you activated the `.venv` for that app |
| "Missing credentials" error | Check that your `.env` file exists and has the right values |
| Widget not showing in Copilot | Verify tunnel is running + URLs in `ai-plugin.json` match |
| "Salesforce auth failed" | Check `SF_CLIENT_ID` / `SF_CLIENT_SECRET` and that Client Credentials Flow is enabled |
| ServiceNow 401 error | For OAuth: enable `client_credential.grant_type.enabled` property. For Basic: check username/password |
| SAP empty results | Verify `SAP_API_KEY` is valid at [api.sap.com](https://api.sap.com) |
| HubSpot 403 error | Check that your Private App has the required scopes enabled |

---

## 10. Authentication Deep Dive

This section explains **how authentication works under the hood** for each LOB system — what protocol is used, how tokens flow, when they expire, and how the MCP server handles them. Understanding this helps with debugging and production hardening.

---

### 🏛️ Salesforce — OAuth 2.0 Client Credentials

```
┌──────────────┐     POST /services/oauth2/token      ┌───────────────────┐
│  MCP Server  │  ─────────────────────────────────►   │  Salesforce Org   │
│  (port 3000) │     grant_type=client_credentials     │                   │
│              │     client_id=...                      │  Token Endpoint   │
│              │     client_secret=...                  │                   │
│              │  ◄─────────────────────────────────   │                   │
│              │     { "access_token": "00D..." }       └───────────────────┘
│              │
│              │     GET /services/data/v62.0/query     ┌───────────────────┐
│              │  ─────────────────────────────────►   │  Salesforce REST  │
│              │     Authorization: Bearer 00D...       │  API              │
│              │  ◄─────────────────────────────────   │                   │
│              │     { "records": [...] }               └───────────────────┘
└──────────────┘
```

| Aspect | Detail |
|---|---|
| **Protocol** | OAuth 2.0 Client Credentials Grant |
| **Credentials** | `SF_CLIENT_ID` + `SF_CLIENT_SECRET` (from Connected App) |
| **Token type** | Bearer access token |
| **Token lifetime** | ~2 hours (session timeout) |
| **Auto-refresh** | Yes — `salesforce.py` caches the token and refreshes 5 minutes before expiry |
| **Retry on 401** | Yes — clears cached token and re-authenticates once |
| **No user interaction** | Correct — this is machine-to-machine (M2M) auth, no browser login needed |

**How the Connected App works:**
1. You create a Connected App in Salesforce Setup with OAuth enabled
2. The app gets a Consumer Key (client_id) and Consumer Secret (client_secret)
3. You assign a "Run As" user — this user's permissions determine what the API can access
4. The MCP server exchanges these credentials for a short-lived access token
5. All API calls use `Authorization: Bearer {token}` header

**Security notes:**
- The Client Secret is a long-lived credential — treat it like a password
- The Run As user should have minimal permissions (principle of least privilege)
- Enable IP restrictions on the Connected App for production use
- Rotate the Client Secret periodically via Setup → App Manager

---

### 🎫 ServiceNow — OAuth 2.0 or Basic Auth

ServiceNow supports two authentication modes. The MCP server auto-selects based on `SERVICENOW_AUTH_MODE`.

#### Option A: OAuth 2.0 Client Credentials (recommended)

```
┌──────────────┐     POST /oauth_token.do              ┌───────────────────┐
│  MCP Server  │  ─────────────────────────────────►   │  ServiceNow PDI   │
│  (port 3001) │     grant_type=client_credentials     │                   │
│              │     client_id=...                      │  OAuth Endpoint   │
│              │     client_secret=...                  │                   │
│              │  ◄─────────────────────────────────   │                   │
│              │     { "access_token": "..." }          └───────────────────┘
│              │
│              │     GET /api/now/table/incident        ┌───────────────────┐
│              │  ─────────────────────────────────►   │  ServiceNow       │
│              │     Authorization: Bearer ...          │  Table API        │
└──────────────┘                                        └───────────────────┘
```

| Aspect | Detail |
|---|---|
| **Protocol** | OAuth 2.0 Client Credentials Grant |
| **Credentials** | `SERVICENOW_CLIENT_ID` + `SERVICENOW_CLIENT_SECRET` (from Application Registry) |
| **Token lifetime** | ~30 minutes (configurable in ServiceNow) |
| **Prerequisite** | Must enable system property `glide.oauth.inbound.client.credential.grant_type.enabled = true` |
| **OAuth Application User** | The user assigned in the Application Registry entry — determines API permissions |

#### Option B: Basic Auth (simpler, for development)

```
┌──────────────┐     GET /api/now/table/incident        ┌───────────────────┐
│  MCP Server  │  ─────────────────────────────────►   │  ServiceNow PDI   │
│  (port 3001) │     Authorization: Basic base64(u:p)   │  Table API        │
│              │  ◄─────────────────────────────────   │                   │
│              │     { "result": [...] }                └───────────────────┘
└──────────────┘
```

| Aspect | Detail |
|---|---|
| **Protocol** | HTTP Basic Authentication |
| **Credentials** | `SERVICENOW_USERNAME` + `SERVICENOW_PASSWORD` (admin credentials from PDI dashboard) |
| **Token lifetime** | N/A — credentials sent with every request |
| **No setup needed** | Just use the admin username/password shown when you create the PDI |

**Security notes:**
- Basic Auth sends credentials with every request (base64-encoded, not encrypted) — use only over HTTPS
- OAuth is preferred for anything beyond local development
- PDI credentials reset when the instance hibernates (after ~hours of inactivity)
- The PDI admin password is shown on the ServiceNow developer dashboard — bookmark it

---

### 📦 SAP S/4HANA — API Key (Sandbox) or Basic Auth (Tenant)

The SAP MCP server operates in **dual mode** controlled by `SAP_MODE`.

#### Sandbox Mode (default — read-only)

```
┌──────────────┐     GET /sap/opu/odata/sap/...        ┌───────────────────┐
│  MCP Server  │  ─────────────────────────────────►   │  SAP API Business │
│  (port 3002) │     apikey: {SAP_API_KEY}              │  Hub Sandbox      │
│              │     Accept: application/json            │                   │
│              │  ◄─────────────────────────────────   │                   │
│              │     { "d": { "results": [...] } }     └───────────────────┘
└──────────────┘
```

| Aspect | Detail |
|---|---|
| **Protocol** | API Key in HTTP header |
| **Credentials** | `SAP_API_KEY` (free from [api.sap.com](https://api.sap.com) profile) |
| **Token lifetime** | Permanent (until you regenerate it) |
| **Read-only** | GET requests only — POST/PUT/PATCH return mock demo data |
| **No user setup** | Just register on api.sap.com and copy the key |
| **Rate limits** | Shared sandbox — be gentle |

#### Tenant Mode (full CRUD — requires real S/4HANA)

```
┌──────────────┐     GET /sap/opu/odata/sap/...        ┌───────────────────┐
│  MCP Server  │  ─────────────────────────────────►   │  S/4HANA Cloud    │
│  (port 3002) │     Authorization: Basic base64(u:p)   │  Tenant           │
│              │  ◄─────────────────────────────────   │                   │
│              │     { "d": { "results": [...] } }     └───────────────────┘
└──────────────┘
```

| Aspect | Detail |
|---|---|
| **Protocol** | HTTP Basic Authentication (Communication User) |
| **Credentials** | `SAP_USERNAME` + `SAP_PASSWORD` (from Communication Arrangement in S/4HANA) |
| **Full CRUD** | All operations work against your real data |
| **Setup required** | Create Communication System → Communication User → Communication Arrangement for each API |

**Security notes:**
- The API key is tied to your personal SAP account — don't share it publicly
- In tenant mode, the Communication User should have only the Communication Scenarios needed (e.g., `SAP_COM_0008` for Business Partners)
- SAP OData responses default to XML — the client adds `Accept: application/json` header

---

### 🧡 HubSpot — Private App Token (Bearer)

```
┌──────────────┐     GET /marketing/v3/emails           ┌───────────────────┐
│  MCP Server  │  ─────────────────────────────────►   │  HubSpot API      │
│  (port 3003) │     Authorization: Bearer pat-na1-...  │  (api.hubapi.com) │
│              │  ◄─────────────────────────────────   │                   │
│              │     { "results": [...] }               └───────────────────┘
└──────────────┘
```

| Aspect | Detail |
|---|---|
| **Protocol** | Bearer Token (Private App) |
| **Credentials** | `HUBSPOT_ACCESS_TOKEN` (from Settings → Integrations → Private Apps) |
| **Token lifetime** | Permanent (until you rotate it) |
| **Token format** | `pat-na1-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| **Scopes** | Defined at creation time — controls which APIs the token can access |
| **Shown once** | The token is displayed only once at creation — copy it immediately |

**Required scopes for this app:**
- `crm.objects.contacts.read` — read contacts in lists
- `crm.objects.contacts.write` — add/remove contacts from lists
- `crm.objects.lists.read` — view contact lists
- `crm.objects.lists.write` — modify list membership
- `content` — read marketing emails and stats

**Security notes:**
- The Private App token is a long-lived bearer token — treat it like an API key
- It's scoped: even if leaked, it can only do what the scopes allow
- To rotate: go to the Private App → click "Rotate token" → update your `.env`
- HubSpot rate limits: 100 requests per 10 seconds, 250,000 per day on the free tier
- Unlike OAuth flows, there's no refresh — the token works until rotated or revoked

---

### Authentication Comparison at a Glance

| LOB | Auth Type | Credentials Needed | Token Lifetime | Auto-Refresh | Free Tier |
|---|---|---|---|---|---|
| **Salesforce** | OAuth 2.0 Client Credentials | Client ID + Secret | ~2 hours | ✅ Yes | ✅ Dev Org |
| **ServiceNow** | OAuth 2.0 or Basic Auth | Client ID + Secret (or user/pass) | ~30 min (OAuth) | ✅ OAuth only | ✅ PDI |
| **SAP** | API Key (sandbox) / Basic (tenant) | API Key or user/pass | Permanent / per-session | N/A | ✅ API Hub |
| **HubSpot** | Bearer Token (Private App) | Access Token | Permanent | N/A | ✅ Free CRM |

> 💡 **Key takeaway:** All four LOBs use different auth patterns, but the MCP servers abstract this away completely. You set credentials once in `.env`, and the server handles token management, caching, and retry logic automatically.
