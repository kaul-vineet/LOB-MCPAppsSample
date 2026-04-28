"""
Regenerate mcp-tools.json and ai-plugin*.json from live server tool definitions.
Run via: gateway\\.venv\\Scripts\\python deploy\\regen_manifests.py
(SetSail calls this automatically before building the zip.)
"""
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent

for lob_dir in ["sf-mcp-app", "snow-mcp-app", "sap-mcp-app",
                "hubspot-mcp-app", "flight-mcp-app", "docusign-mcp-app",
                "saphr-mcp-app", "workday-mcp-app", "coupa-mcp-app", "jira-mcp-app"]:
    env = ROOT / lob_dir / ".env"
    if env.exists():
        load_dotenv(env, override=False)

import coupa_mcp.coupa_server as coupa
import docusign_mcp.docusign_server as ds
import flight_mcp.flight_server as ft
import hubspot_mcp.hubspot_server as hs
import jira_mcp.jira_server as jira
import sap_s4hana_mcp.sap_server as sap
import saphr_mcp.saphr_server as saphr
import servicenow_mcp.servicenow_server as sn
import sf_crm_mcp.salesforce_server as sf
import workday_mcp.workday_server as workday

SERVERS = [
    (sf,      "sf",      "/sf/mcp"),
    (sn,      "sn",      "/sn/mcp"),
    (sap,     "sap",     "/sap/mcp"),
    (hs,      "hs",      "/hs/mcp"),
    (ft,      "ft",      "/ft/mcp"),
    (ds,      "ds",      "/ds/mcp"),
    (saphr,   "saphr",   "/saphr/mcp"),
    (workday, "workday", "/workday/mcp"),
    (coupa,   "coupa",   "/coupa/mcp"),
    (jira,    "jira",    "/jira/mcp"),
]

TUNNEL_BASE = os.getenv("MCP_GATEWAY_URL", "https://1pgd9z7m-8080.inc1.devtunnels.ms")


def title_case(name: str) -> str:
    bare = re.sub(r"^[a-z]+__", "", name)
    return bare.replace("_", " ").capitalize()


def clean_schema(schema: dict) -> dict:
    """Strip Pydantic artifacts not in the MCP spec inputSchema format."""
    s = {k: v for k, v in schema.items() if k != "title"}
    if "properties" in s:
        s["properties"] = {
            pname: {pk: pv for pk, pv in prop.items() if pk != "title"}
            for pname, prop in s["properties"].items()
        }
    return s


def build_entries(server_mod):
    tools = server_mod.mcp._tool_manager._tools
    entries, functions = [], []
    for tool_name, tool in tools.items():
        schema = dict(tool.parameters) if tool.parameters else {
            "properties": {}, "type": "object"
        }
        schema.setdefault("required", [])
        entry = {
            "name": tool_name,
            "description": tool.description or "",
            "inputSchema": clean_schema(schema),
            "title": title_case(tool_name),
        }
        if tool.meta:
            entry["_meta"] = tool.meta
        entries.append(entry)
        functions.append({"name": tool_name, "description": tool.description or ""})
    return entries, functions


all_entries, all_functions, runtimes = [], [], []

for server_mod, prefix, path in SERVERS:
    entries, functions = build_entries(server_mod)
    all_entries.extend(entries)
    all_functions.extend(functions)
    runtimes.append({"prefix": prefix, "path": path, "functions": functions})

# ── mcp-tools.json ────────────────────────────────────────────────────────────
tools_path = ROOT / "lob-agent" / "appPackage" / "mcp-tools.json"
tools_path.write_text(json.dumps({"tools": all_entries}, indent=4), encoding="utf-8")
print(f"[OK] mcp-tools.json — {len(all_entries)} tools")

# ── ai-plugin.json (source) + ai-plugin.dev.json (build) ─────────────────────
for plugin_path in [
    ROOT / "lob-agent" / "appPackage" / "ai-plugin.json",
    ROOT / "lob-agent" / "appPackage" / "build" / "ai-plugin.dev.json",
]:
    plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
    plugin["functions"] = all_functions
    existing = plugin.get("runtimes", [])
    new_runtimes = []
    for i, rt in enumerate(runtimes):
        base = existing[i] if i < len(existing) else {
            "type": "RemoteMCPServer",
            "spec": {"url": "", "mcp_tool_description": {"file": "mcp-tools.json"}},
            "auth": {"type": "None"},
        }
        base["spec"]["url"] = TUNNEL_BASE + rt["path"]
        base["run_for_functions"] = [f["name"] for f in rt["functions"]]
        new_runtimes.append(base)
    plugin["runtimes"] = new_runtimes
    if plugin_path.exists():
        plugin_path.chmod(plugin_path.stat().st_mode | 0o200)
    plugin_path.write_text(json.dumps(plugin, indent=4), encoding="utf-8")
    print(f"[OK] {plugin_path.name} — {len(all_functions)} functions, {len(new_runtimes)} runtimes")

for rt in runtimes:
    print(f"  {rt['prefix']:8s}  {len(rt['functions']):2d} tools  {rt['path']}")
