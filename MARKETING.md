# 🚀 The Great Trading Company — LOB MCP Apps for M365 Copilot

## What is this?

A **production-ready reference implementation** that connects four enterprise LOB systems to Microsoft 365 Copilot through the Model Context Protocol (MCP). One agent, four backends, interactive widgets — all rendered directly inside M365 Copilot chat with side-by-side support.

## The Problem

Enterprises run on fragmented LOB systems — Salesforce for CRM, ServiceNow for ITSM, SAP for ERP, HubSpot for marketing. Employees context-switch between portals dozens of times a day. What if they could manage all four from a single conversational interface?

## The Solution

**The Great Trading Company** is a declarative agent for M365 Copilot that connects to four Python MCP servers, each wrapping a real LOB API. Users interact through natural language — the agent routes to the right system, calls the right tool, and renders an interactive widget with live data. No portal switching. No tab overload.

## ✨ Key Highlights

### 🏢 Four Enterprise LOB Systems

| System | What it does | API |
|--------|-------------|-----|
| **Salesforce CRM** | Leads, Opportunities — full CRUD pipeline | REST API v62.0 |
| **ServiceNow ITSM** | Incidents, Service Requests, Request Items — triage & fulfillment | Table API |
| **SAP S/4HANA** | Purchase Orders, Materials, Business Partners — procurement cycle | OData v4 |
| **HubSpot Marketing** | Email campaigns, Contact Lists, Subscribers — 3-level drill-down | REST API |

### 🎨 React + Fluent UI Widgets with LOB-Native Design

Each widget is styled to match its LOB's native design language — not generic Fluent UI defaults:

- **Salesforce** → Lightning Design System (SLDS): blue headers, pill badges, compact forms
- **SAP** → Fiori: shell bar, '72' font, semantic status badges, Object Page layout
- **HubSpot** → Canvas: metric cards, percentage bars, coral/teal palette
- **ServiceNow** → Now Design: teal shell, P1-P4 priority colors, expandable request rows

### 🔌 MCP Apps Protocol — Official Implementation

Built on `@modelcontextprotocol/ext-apps` — the official MCP Apps standard for widget delivery:

- **Handshake**: `ui/initialize` → `ui/notifications/initialized` → `ui/notifications/tool-result`
- **callTool**: `app.callServerTool()` with automatic retry on failure
- **Side-by-side**: `app.requestDisplayMode({ mode: 'fullscreen' })` — widget expands alongside chat
- **Theming**: Auto light/dark via host context
- **Error boundaries**: Widget crashes show recovery UI, not white screens

### 🐳 Docker-First, One-Command Startup

```bash
.\SetSail.ps1    # Starts Docker containers + dev tunnel in one command
```

Four containers, four ports, one tunnel, one agent. Or run natively with Python venvs.

### 🧰 Templatized for Any LOB

Fork it, copy an app folder, connect your own system:

1. Copy `sf-mcp-app/` → `your-lob-app/`
2. Replace the API client
3. Rewrite the MCP tools
4. Build a React widget (or use vanilla HTML)
5. Add to the agent manifest

The shared infrastructure handles: MCP protocol, Docker, tunnel, agent provisioning, test harness, widget build pipeline.

## 📊 Architecture at a Glance

```
M365 Copilot Chat
  │
  ├── Declarative Agent (lob-agent/)
  │     ├── instruction.txt (business process routing)
  │     ├── ai-plugin.json (4 runtimes, 27 tools)
  │     └── mcp-tools.json (tool schemas + widget URIs)
  │
  └── Dev Tunnel (anonymous, 4 ports)
        │
        ├── :3000 → Salesforce MCP Server (Python)
        │            └── React widget (SLDS themed)
        ├── :3001 → ServiceNow MCP Server (Python)
        │            └── React widget (Now themed)
        ├── :3002 → SAP MCP Server (Python)
        │            └── React widget (Fiori themed)
        └── :3003 → HubSpot MCP Server (Python)
                     └── React widget (Canvas themed)
```

## 🎯 What Makes This Different

| Feature | This Project | Typical MCP Demo |
|---------|-------------|-----------------|
| **LOB systems** | 4 real enterprise APIs | 1 toy API |
| **Widget design** | LOB-native (SLDS, Fiori, Canvas, Now) | Generic Fluent |
| **CRUD operations** | Full create/read/update across all 4 | Read-only |
| **Side-by-side** | ✅ Expand widget alongside chat | ❌ |
| **Multi-LOB routing** | One agent routes to 4 backends | One agent, one backend |
| **Docker support** | One-command startup | Manual Python venvs |
| **Test harness** | MCP Apps protocol simulator | None |
| **Error handling** | Error boundaries, retry, toast | Crash |
| **Templatized** | Copy a folder, connect any LOB | Monolithic |

## 🔗 Links

- **Repository**: [github.com/kaul-vineet/LOB-MCPAppsSample](https://github.com/kaul-vineet/LOB-MCPAppsSample)
- **Microsoft MCP Interactive UI Samples**: [github.com/microsoft/mcp-interactiveUI-samples](https://github.com/microsoft/mcp-interactiveUI-samples)
- **MCP Apps Spec**: [modelcontextprotocol.github.io/ext-apps](https://modelcontextprotocol.github.io/ext-apps)
- **M365 Widget UX Guidelines**: [learn.microsoft.com/.../declarative-agent-ui-widgets-guidelines](https://learn.microsoft.com/microsoft-365/copilot/extensibility/declarative-agent-ui-widgets-guidelines)

---

*Built by Vineet Kaul, PM Architect – Agentic AI, Microsoft*
