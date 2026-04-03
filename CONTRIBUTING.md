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
