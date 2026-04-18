# LOB-MCP-Apps — Copilot Session Context
## Last Updated: 2026-04-18 | Session: 4844666b

> **Purpose**: Portable session context for GitHub Copilot CLI. Start a new session and say:
> "Read this gist for project context: <gist-url>"

---

## 🚢 Platform Metrics (Current State)

| Metric | Value |
|--------|-------|
| **LOBs** | 6 (Salesforce, ServiceNow, SAP, HubSpot, Flight Tracker, DocuSign) |
| **Total Tools** | 62 |
| **React Widgets** | 6 (all Fluent UI v9, Vite single-file) |
| **Manifest Functions** | 62 (ai-plugin.json) |
| **Ports** | SF=3000, SN=3001, SAP=3002, HS=3003, Flight=3004, DocuSign=3005 |

### Tool Breakdown by LOB

| LOB | Read | Write | Form | Other | Total |
|-----|------|-------|------|-------|-------|
| Salesforce | 4 | 6 | 3 | 2 update | **15** |
| ServiceNow | 4 | 5 | 2 | 2 update | **13** |
| SAP | 4 | 2 | — | — | **6** |
| HubSpot | 5 | 3 | 2 | 4 list mgmt | **14** |
| Flight | 5 | — | — | — | **5** |
| DocuSign | 4 | 3 | 1 | 1 download | **9** |

---

## 🏗️ Key Architecture Patterns

### Tool-Call Looping Fix (CRITICAL)
M365 Copilot agent loops calling tools repeatedly when text summary is vague.
**Fix**: Always include actual record data in `TextContent` alongside `structuredContent` widget.

### Form Tool Pattern
```python
@mcp.tool(meta={"ui": {"resourceUri": WIDGET_URI}})
async def sf__create_lead_form() -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="Opening Lead form.")],
        structuredContent={"type": "form", "entity": "lead"},
    )
```
Widget `App.tsx` checks `data.type === 'form'` → renders `<FormView>` component.

### Widget Build Pipeline
```
widgets/src/{name}/ → (index.html, main.tsx, App.tsx, types.ts)
   ↓ node build.mjs (Vite + vite-plugin-singlefile)
widgets/dist/{name}.html
   ↓ copy
{lob}-mcp-app/{lob}_mcp/web/widget.html
```

### Naming Convention
- **ai-plugin.json**: single underscore → `sf_create_lead_form`
- **server.py tool**: double underscore → `sf__create_lead_form`

### Shared Widget Components
`widgets/src/shared/`: McpBridge.tsx, FluentWrapper.tsx, Toast.tsx, ErrorBoundary.tsx, ExpandButton.tsx, McpFooter.tsx

---

## 📊 ESS-MCP Comparison (scadam/ess-mcp)

| Dimension | ESS-MCP | LOB-MCP-Apps | Gap |
|-----------|---------|--------------|-----|
| LOBs | 4 | **6** | ✅ We lead |
| Total Tools | **142** | 62 | 80 gap |
| Widgets | **42** | 6 | 36 gap |
| Form Tools | ~30 | 8 | 22 gap |
| Callback Tools | ~30 | 0 | 30 gap |
| Write Tools | ~30 | 20 | 10 gap |
| Widget Tech | Raw HTML+Skybridge | **React+Fluent UI** | ✅ We lead |
| Deployment | **Azure Container Apps (Bicep)** | Docker Compose | Gap |

---

## ✅ Improvement Backlog Status

| # | Item | Status |
|---|------|--------|
| 1 | Form Widget Tools | ✅ Done (8 form tools) |
| 2 | Widget Callbacks | ❌ Pending (~30 tools in ESS-MCP) |
| 3 | Write/Action Tools | ✅ Done (20 write tools) |
| 4 | Shared Code Library | ❌ Pending |
| 5 | ASGI Gateway | ❌ Pending |
| 6 | Cross-System Workflows | ❌ Pending |
| 7 | Dark/Light Mode | ✅ Already implemented |
| 8 | Tool Naming Convention | ✅ Done |
| 9 | Retry/Resilience | ✅ Done (tenacity) |
| 10 | IaC Deployment | ❌ Pending |
| 11 | Protocol Validation | ❌ Pending |
| 12 | Typed Config | ✅ Done (pydantic-settings) |
| 13 | Structured Logging | ✅ Done (structlog) |
| 14 | LOB Expansion | ✅ Done (4→6 LOBs) |
| 15 | Gallery/Demo Page | ✅ Done |

---

## 🔧 Git Commits This Session (10)

| # | SHA | Description |
|---|-----|-------------|
| 1 | `e2232f3` | Set-Sail.ps1 ASCII art, SNOW _val() fix, widget color fix |
| 2 | `9f20070` | Detailed text summaries for all servers (tool-loop fix) |
| 3 | `010ebc7` | Beautified GitHub Pages gallery |
| 4 | `0c9090b` | Heading font + CSS logo icons |
| 5 | `211cfd0` | Tool naming, structlog, pydantic-settings, tenacity |
| 6 | `6333464` | 14 write tools (SF/SN/HS) |
| 7 | `496d6af` | Flight Tracker as 5th LOB |
| 8 | `679422d` | DocuSign as 6th LOB |
| 9 | `cde6aac` | SF FormView + 3 form tools |
| 10 | `a2543fc` | Form widgets + React rewrites (all LOBs) |

---

## ⚠️ Known Issues

1. **SAP widget shimmer**: M365 Copilot host caching — needs agent app package re-upload
2. **DocuSign form tool**: Uses list-of-dicts return pattern instead of `types.CallToolResult` with `structuredContent` (inconsistent with SF/SN/HS)
3. **Flight & DocuSign**: Untested against live APIs (need credentials)
4. **`__pycache__`**: Two dirs accidentally committed in `a2543fc` (docusign, flight)

---

## 📁 Key Files

| File | Lines | What |
|------|-------|------|
| `widgets/src/salesforce/App.tsx` | ~965 | SF widget + FormView |
| `widgets/src/servicenow/App.tsx` | ~1105 | SN widget + FormView |
| `widgets/src/hubspot/App.tsx` | ~1450 | HS widget + FormView |
| `widgets/src/flight/App.tsx` | 612 | Flight widget (side-by-side) |
| `widgets/src/docusign/App.tsx` | 560 | DocuSign widget + send form |
| `lob-agent/appPackage/ai-plugin.json` | ~410 | 62 functions, 6 runtimes |
| `widgets/build.mjs` | 40 | Vite build script |
| `docker-compose.yml` | ~102 | All 6 services |
