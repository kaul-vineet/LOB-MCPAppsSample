"""
Regenerate mcp-tools.json and ai-plugin.json from live server tool definitions.
Run from project root: python regen_manifests.py
"""
import json
import re
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent

# Pre-load all .env files
for lob_dir in ["sf-mcp-app", "snow-mcp-app", "sap-mcp-app",
                 "hubspot-mcp-app", "flight-mcp-app", "docusign-mcp-app"]:
    env = ROOT / lob_dir / ".env"
    if env.exists():
        load_dotenv(env, override=False)

import docusign_mcp.server as ds
import flight_mcp.server as ft
import hubspot_mcp.server as hs
import sap_s4hana_mcp.server as sap
import servicenow_mcp.server as sn
import sf_crm_mcp.server as sf

# (server_module, runtime_prefix, gateway_path)
SERVERS = [
    (sf,  "sf",  "/sf/mcp"),
    (sn,  "sn",  "/sn/mcp"),
    (sap, "sap", "/sap/mcp"),
    (hs,  "hs",  "/hs/mcp"),
    (ft,  "ft",  "/ft/mcp"),
    (ds,  "ds",  "/ds/mcp"),
]

TUNNEL_BASE = "https://1pgd9z7m-8080.inc1.devtunnels.ms"

def title_case(name: str) -> str:
    """sf__get_leads -> Get leads"""
    bare = re.sub(r"^[a-z]+__", "", name)
    return bare.replace("_", " ").capitalize()


def build_entries(server_mod):
    tools = server_mod.mcp._tool_manager._tools
    entries = []
    functions = []
    for tool_name, tool in tools.items():
        schema = dict(tool.parameters) if tool.parameters else {
            "properties": {}, "title": f"{tool_name}Arguments", "type": "object"
        }
        if "required" not in schema:
            schema["required"] = []
        entry = {
            "name": tool_name,
            "description": tool.description or "",
            "inputSchema": schema,
            "title": title_case(tool_name),
        }
        if tool.meta:
            entry["_meta"] = tool.meta
        entries.append(entry)
        functions.append({
            "name": tool_name,
            "description": tool.description or "",
        })
    return entries, functions


all_tool_entries = []
runtimes = []
all_functions = []

for server_mod, prefix, path in SERVERS:
    entries, functions = build_entries(server_mod)
    all_tool_entries.extend(entries)
    all_functions.extend(functions)
    runtimes.append({
        "prefix": prefix,
        "path": path,
        "function_names": [f["name"] for f in functions],
    })

# ── Write mcp-tools.json ──────────────────────────────────────────────────────
tools_path = ROOT / "lob-agent" / "appPackage" / "mcp-tools.json"
tools_data = {"tools": all_tool_entries}
tools_path.write_text(json.dumps(tools_data, indent=4), encoding="utf-8")
print(f"[OK] mcp-tools.json — {len(all_tool_entries)} tools written")

# ── Update ai-plugin.json ─────────────────────────────────────────────────────
plugin_path = ROOT / "lob-agent" / "appPackage" / "ai-plugin.json"
plugin = json.loads(plugin_path.read_text(encoding="utf-8"))

plugin["functions"] = all_functions

for i, rt_meta in enumerate(runtimes):
    plugin["runtimes"][i]["spec"]["url"] = (
        TUNNEL_BASE + rt_meta["path"]
    )
    plugin["runtimes"][i]["run_for_functions"] = rt_meta["function_names"]

plugin_path.write_text(json.dumps(plugin, indent=4), encoding="utf-8")
print(f"[OK] ai-plugin.json — {len(all_functions)} functions, {len(runtimes)} runtimes updated")

# ── Summary ───────────────────────────────────────────────────────────────────
for rt_meta in runtimes:
    print(f"  {rt_meta['prefix']:4s}  {len(rt_meta['function_names']):2d} tools  {rt_meta['path']}")
