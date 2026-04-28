"""
check_meta.py — Validate mcp-tools.json against server tool definitions.

Catches three classes of drift:
  1. Tools in mcp-tools.json missing _meta.ui.resourceUri
  2. Tools in mcp-tools.json not registered in ai-plugin.json
  3. Tools defined in *_server.py not present in mcp-tools.json

Usage:
    gateway\\.venv\\Scripts\\python deploy\\check_meta.py
    gateway\\.venv\\Scripts\\python deploy\\check_meta.py --verbose
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

SERVERS = {
    "salesforce": ROOT / "sf-mcp-app"       / "sf_crm_mcp"       / "salesforce_server.py",
    "servicenow": ROOT / "snow-mcp-app"     / "servicenow_mcp"    / "servicenow_server.py",
    "sap":        ROOT / "sap-mcp-app"      / "sap_s4hana_mcp"    / "sap_server.py",
    "hubspot":    ROOT / "hubspot-mcp-app"  / "hubspot_mcp"        / "hubspot_server.py",
    "flight":     ROOT / "flight-mcp-app"   / "flight_mcp"        / "flight_server.py",
    "docusign":   ROOT / "docusign-mcp-app" / "docusign_mcp"       / "docusign_server.py",
    "saphr":      ROOT / "saphr-mcp-app"    / "saphr_mcp"         / "saphr_server.py",
    "workday":    ROOT / "workday-mcp-app"  / "workday_mcp"        / "workday_server.py",
    "coupa":      ROOT / "coupa-mcp-app"    / "coupa_mcp"         / "coupa_server.py",
    "jira":       ROOT / "jira-mcp-app"     / "jira_mcp"          / "jira_server.py",
}

MCP_TOOLS_JSON = ROOT / "lob-agent" / "appPackage" / "mcp-tools.json"
AI_PLUGIN_JSON = ROOT / "lob-agent" / "appPackage" / "ai-plugin.json"

_STRIP_PREFIXES = (
    "sf__", "sn__", "sap__", "hs__", "ft__", "ds__",
    "saphr__", "wday__", "coupa__", "jira__",
    "sf_",  "sn_",  "sap_",  "hs_",  "ft_",  "ds_",
    "saphr_", "wday_", "coupa_", "jira_",
)


def _normalise(name: str) -> str:
    for prefix in _STRIP_PREFIXES:
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def load_mcp_tools() -> list[dict]:
    return json.loads(MCP_TOOLS_JSON.read_text(encoding="utf-8")).get("tools", [])


def load_ai_plugin_functions() -> set[str]:
    return {f.get("name", "") for f in
            json.loads(AI_PLUGIN_JSON.read_text(encoding="utf-8")).get("functions", [])}


def parse_server_tools(path: Path) -> list[dict]:
    src = path.read_text(encoding="utf-8")
    tools = []
    for m in re.finditer(r'@mcp\.tool\((.*?)\)\s*\nasync def (\w+)', src, re.DOTALL):
        decorator_args, func_name = m.group(1), m.group(2)
        has_meta = bool(re.search(r'\bmeta\s*=', decorator_args))
        uri_match = re.search(r'resourceUri["\s]*:\s*["\']([^"\']+)["\']', decorator_args)
        resource_uri = uri_match.group(1) if uri_match else ("<variable>" if has_meta else None)
        tools.append({"name": func_name, "resourceUri": resource_uri})
    return tools


def check(verbose: bool = False) -> bool:
    ok = True
    print("=" * 60)
    print("check_meta.py — MCP tool manifest validation")
    print("=" * 60)

    manifest_tools = load_mcp_tools()
    manifest_names = {t["name"] for t in manifest_tools}
    plugin_functions = load_ai_plugin_functions()

    print("\n[1] _meta.ui.resourceUri on all mcp-tools.json entries")
    missing_meta = [t["name"] for t in manifest_tools
                    if not t.get("_meta", {}).get("ui", {}).get("resourceUri")]
    if missing_meta:
        ok = False
        for name in missing_meta:
            print(f"  [FAIL] MISSING _meta: {name}")
    else:
        print(f"  [OK] All {len(manifest_tools)} tools have _meta.ui.resourceUri")

    print("\n[2] mcp-tools.json tools present in ai-plugin.json functions")
    not_in_plugin = [n for n in manifest_names if n not in plugin_functions]
    if not_in_plugin:
        ok = False
        for name in sorted(not_in_plugin):
            print(f"  [FAIL] NOT in ai-plugin.json: {name}")
    else:
        print(f"  [OK] All {len(manifest_names)} manifest tools found in ai-plugin.json")

    print("\n[3] *_server.py tools vs mcp-tools.json (prefix-normalised)")
    for lob, path in SERVERS.items():
        if not path.exists():
            print(f"  [WARN] {lob}: {path.name} not found")
            continue
        server_tools = parse_server_tools(path)
        if not server_tools:
            print(f"  [WARN] {lob}: no @mcp.tool decorators found")
            continue
        server_norm = {_normalise(t["name"]) for t in server_tools}
        manifest_norm = {_normalise(n) for n in manifest_names}
        unmanifested = server_norm - manifest_norm
        if unmanifested:
            ok = False
        if verbose:
            print(f"\n  {lob} ({len(server_tools)} tools):")
            for t in server_tools:
                norm = _normalise(t["name"])
                status = "[OK]" if norm in manifest_norm else "[FAIL] not manifested"
                meta = "meta[OK]" if t["resourceUri"] else "meta[FAIL]"
                print(f"    {status:24s}  {meta}  {t['name']}")
        elif unmanifested:
            print(f"  [FAIL] {lob}: unmanifested tools: {', '.join(sorted(unmanifested))}")
        else:
            print(f"  [OK] {lob}: all {len(server_tools)} tools accounted for")

    print("\n" + "=" * 60)
    print("[OK] All checks passed" if ok else "[FAIL] Drift detected — run regen_manifests.py")
    print("=" * 60)
    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    sys.exit(0 if check(verbose=args.verbose) else 1)
