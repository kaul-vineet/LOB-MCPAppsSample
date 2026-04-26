# Contributing to The Great Trading Company

Thank you for your interest in expanding the Company's trading empire! 🚢

## How to contribute

### Adding a new LOB app

This is the most common contribution. See the [Scaffolding Guide](README.md#-using-this-as-a-scaffolding) in the README for the full walkthrough. In short:

1. Copy an existing app folder as your template
2. Replace the API client with your LOB's auth + REST calls
3. Rewrite `server.py` tools for your entity types
4. Build your widget HTML
5. Wire into `lob-agent/appPackage/` (ai-plugin, mcp-tools, instruction)
6. Add a test harness with mock data
7. Update the README and SETUP.md

### Module naming convention

Every server package uses a strict `{domain}_` prefix on all module files:

```
{domain}_client.py    — HTTP client for the LOB API (auth, requests, mock data)
{domain}_server.py    — MCP server bootstrap only (register tools, start uvicorn)
{domain}_settings.py  — Pydantic settings / env var loading only
{domain}_tools.py     — Tool handler functions + TOOL_SPECS registry
__init__.py           — Empty or minimal public re-exports
__main__.py           — Entry point: `from .{domain}_server import main`
```

Examples: `salesforce_client.py`, `servicenow_server.py`, `sap_settings.py`.
The `{domain}` matches the package folder name (e.g. `servicenow_mcp` → `servicenow`).

### Single Responsibility Principle (SRP)

Each file has exactly one responsibility — violations are rejected in review:

| File | Owns | Must NOT contain |
|------|------|-----------------|
| `{domain}_server.py` | FastMCP bootstrap, tool/prompt registration, uvicorn startup | Tool logic, HTTP calls, settings parsing |
| `{domain}_tools.py` | Tool handler functions, `TOOL_SPECS` list | Server startup, HTTP calls, settings |
| `{domain}_client.py` | HTTP client, auth, mock data, field helpers | Tool specs, server bootstrap, MCP imports |
| `{domain}_settings.py` | Pydantic `BaseSettings` model, `get_settings()` loader | Business logic, tool handlers |
| `shared_mcp/auth.py` | Bearer token extraction | HTTP, logging, settings |
| `shared_mcp/http.py` | `create_async_client()` factory | Auth, business logic |
| `shared_mcp/logger.py` | `get_logger()` wrapper | Anything else |
| `shared_mcp/settings.py` | Shared `BaseSettings` subclasses for all servers | Tool logic, HTTP calls |

Tool spec constant is always named `TOOL_SPECS` (not `{DOMAIN}_TOOL_SPECS`).

### Code style

- **Python:** Follow the patterns in `sf-mcp-app/` (the gold standard)
  - Module-level docstrings on every file
  - Section separators (`# ══ SECTION ══`) between logical blocks
  - Docstrings on all public functions and tools
  - Inline comments on non-obvious logic only (don't over-comment)
- **Widget HTML:** Single-file, self-contained, no build step
  - Use CSS custom properties for theming (light/dark)
  - Use the `postMessage`/`window.openai` bridge pattern — don't invent a new one
  - Include `notifyHeight()` after every render
- **Config files:** Follow existing JSON formatting in `appPackage/`

### Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add Jira MCP app with sprint board widget
fix: ServiceNow OAuth token refresh on 401
docs: add Zendesk setup instructions to SETUP.md
```

### Pull requests

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/jira-mcp-app`
3. Make your changes
4. Test with the widget test harness (open `tests/widget_test.html` in a browser)
5. Verify the server starts: `python -m {your_package}`
6. Submit a PR with a clear description of what LOB you're adding and why

### What makes a good LOB app contribution

- **Free developer instance** available (so others can test without paying)
- **Clean REST API** with standard auth (OAuth, API key, or Bearer token)
- **CRUD operations** that map to the widget pattern (table → create/edit forms)
- **Test harness** with realistic mock data
- **Updated SETUP.md** with step-by-step credential guide

### Reporting issues

- Use GitHub Issues
- Include: which LOB app, what you were trying to do, error message, and your Python/MCP SDK version

## Code of conduct

Be professional, be helpful, expand the empire. 🏛️
