"""
check_meta.py — Validate mcp-tools.json against server.py tool definitions.

Catches three classes of drift without requiring running servers:
  1. Tools in mcp-tools.json missing _meta.ui.resourceUri
  2. Tools in mcp-tools.json not registered in ai-plugin.json
  3. Tools registered in server.py not present in mcp-tools.json
     (after normalising prefix differences like sf__get_leads → get_leads)

Usage:
    python check_meta.py
    python check_meta.py --verbose
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent

SERVERS = {
    "salesforce": ROOT / "sf-mcp-app"  / "sf_crm_mcp"  / "server.py",
    "servicenow": ROOT / "snow-mcp-app" / "servicenow_mcp" / "server.py",
    "sap":        ROOT / "sap-mcp-app"  / "sap_s4hana_mcp" / "server.py",
    "hubspot":    ROOT / "hubspot-mcp-app" / "hubspot_mcp" / "server.py",
    "flight":     ROOT / "flight-mcp-app" / "flight_mcp" / "server.py",
    "docusign":   ROOT / "docusign-mcp-app" / "docusign_mcp" / "server.py",
}

MCP_TOOLS_JSON = ROOT / "lob-agent" / "appPackage" / "mcp-tools.json"
AI_PLUGIN_JSON = ROOT / "lob-agent" / "appPackage" / "ai-plugin.json"

# Prefixes used in server.py function names that are stripped in mcp-tools.json.
# Double-underscore variants must come before single-underscore to avoid partial strips.
_STRIP_PREFIXES = ("sf__", "sn__", "sap__", "hs__", "ft__", "ds__",
                   "sf_",  "sn_",  "sap_",  "hs_",  "ft_",  "ds_")


def _normalise(name: str) -> str:
    """Strip LOB prefix so server.py names can be matched against mcp-tools.json."""
    for prefix in _STRIP_PREFIXES:
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def load_mcp_tools() -> list[dict]:
    data = json.loads(MCP_TOOLS_JSON.read_text(encoding="utf-8"))
    return data.get("tools", [])


def load_ai_plugin_functions() -> set[str]:
    data = json.loads(AI_PLUGIN_JSON.read_text(encoding="utf-8"))
    names: set[str] = set()
    for func in data.get("functions", []):
        names.add(func.get("name", ""))
    return names


def parse_server_tools(path: Path) -> list[dict]:
    """
    Extract tool names and meta resourceUri by scanning server.py for the pattern:

        @mcp.tool(...)           ← optional meta= kwarg
        async def FUNCNAME(...)  ← tool name
    """
    src = path.read_text(encoding="utf-8")
    tools = []

    # Match @mcp.tool(...) blocks followed by async def
    pattern = re.compile(
        r'@mcp\.tool\((.*?)\)\s*\nasync def (\w+)',
        re.DOTALL,
    )
    for m in pattern.finditer(src):
        decorator_args, func_name = m.group(1), m.group(2)
        # Detect meta= presence — may use a variable (e.g. WIDGET_URI) or inline string
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

    # ── Load sources ────────────────────────────────────────────────────────
    manifest_tools = load_mcp_tools()
    manifest_names = {t["name"] for t in manifest_tools}
    plugin_functions = load_ai_plugin_functions()

    # ── Check 1: _meta.ui.resourceUri present on every manifest tool ────────
    print("\n[1] _meta.ui.resourceUri on all mcp-tools.json entries")
    missing_meta = [t["name"] for t in manifest_tools if not t.get("_meta", {}).get("ui", {}).get("resourceUri")]
    if missing_meta:
        ok = False
        for name in missing_meta:
            print(f"  [FAIL] MISSING _meta: {name}")
    else:
        print(f"  [OK] All {len(manifest_tools)} tools have _meta.ui.resourceUri")

    # ── Check 2: every mcp-tools.json tool in ai-plugin.json ────────────────
    print("\n[2] mcp-tools.json tools present in ai-plugin.json functions")
    not_in_plugin = [n for n in manifest_names if n not in plugin_functions]
    if not_in_plugin:
        ok = False
        for name in sorted(not_in_plugin):
            print(f"  [FAIL] NOT in ai-plugin.json: {name}")
    else:
        print(f"  [OK] All {len(manifest_names)} manifest tools found in ai-plugin.json")

    # ── Check 3: server.py tools vs mcp-tools.json ──────────────────────────
    print("\n[3] server.py tools vs mcp-tools.json (after prefix normalisation)")
    for lob, path in SERVERS.items():
        if not path.exists():
            print(f"  [WARN] {lob}: server.py not found at {path}")
            continue

        server_tools = parse_server_tools(path)
        if not server_tools:
            print(f"  [WARN] {lob}: no @mcp.tool decorators found — check regex")
            continue

        server_normalised = {_normalise(t["name"]): t for t in server_tools}
        server_norm_names = set(server_normalised)

        # Tools in server but not in manifest (could be new tools not yet manifested)
        unmanifested = server_norm_names - manifest_names
        # Tools in manifest that match this LOB's server but missing from server
        lob_manifest = {n for n in manifest_names if n in server_norm_names or
                        any(n == _normalise(st["name"]) for st in server_tools)}

        if unmanifested:
            ok = False

        if verbose:
            print(f"\n  {lob} ({len(server_tools)} tools in server.py):")
            for t in server_tools:
                norm = _normalise(t["name"])
                in_manifest = "[OK]" if norm in manifest_names else "[FAIL] not manifested"
                has_meta = "meta[OK]" if t["resourceUri"] else "meta[FAIL]"
                print(f"    {in_manifest:20s}  {has_meta}  {t['name']}")
        else:
            if unmanifested:
                print(f"  [FAIL] {lob}: tools in server.py missing from mcp-tools.json:")
                for name in sorted(unmanifested):
                    print(f"      {name}")
            else:
                print(f"  [OK] {lob}: all {len(server_tools)} server tools accounted for in manifest")

    print("\n" + "=" * 60)
    if ok:
        print("[OK] All checks passed")
    else:
        print("[FAIL] Drift detected -- update mcp-tools.json or server.py")
    print("=" * 60)
    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate MCP tool manifest")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show per-tool detail for every LOB")
    args = parser.parse_args()
    sys.exit(0 if check(verbose=args.verbose) else 1)
