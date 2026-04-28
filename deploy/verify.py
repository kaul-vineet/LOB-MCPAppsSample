"""
GTC Deployment Verifier
Run after SetSail to confirm the package and live servers are correct.

Usage:
    gateway\.venv\Scripts\python deploy\verify.py
"""
import json
import sys
import zipfile
from pathlib import Path

import httpx

ROOT      = Path(__file__).parent.parent
BUILD_DIR = ROOT / "lob-agent" / "appPackage" / "build"
ZIP_PATH  = BUILD_DIR / "appPackage.dev.zip"

PASS = "\033[32m[PASS]\033[0m"
FAIL = "\033[31m[FAIL]\033[0m"
WARN = "\033[33m[WARN]\033[0m"
INFO = "\033[36m[INFO]\033[0m"

errors = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global errors
    status = PASS if ok else FAIL
    print(f"  {status}  {label}" + (f"  — {detail}" if detail else ""))
    if not ok:
        errors += 1


# ── 1. Zip structure ──────────────────────────────────────────────────────────

print()
print("1. Zip structure")
if not ZIP_PATH.exists():
    print(f"  {FAIL}  Zip not found: {ZIP_PATH}")
    sys.exit(1)

z = zipfile.ZipFile(ZIP_PATH)
names = set(z.namelist())
for f in ["manifest.json", "declarativeAgent.json", "ai-plugin.json",
          "color.png", "outline.png"]:
    check(f"contains {f}", f in names)
check("no mcp-tools.json in zip (MOS3 can't resolve file: token)",
      "mcp-tools.json" not in names)

# ── 2. ai-plugin.json schema ──────────────────────────────────────────────────

print()
print("2. ai-plugin.json")
plugin = json.loads(z.read("ai-plugin.json"))

check("schema_version is v2.4", plugin.get("schema_version") == "v2.4",
      plugin.get("schema_version"))
check(f"functions count is 225", len(plugin.get("functions", [])) == 225,
      str(len(plugin.get("functions", []))))
check("10 runtimes", len(plugin.get("runtimes", [])) == 10,
      str(len(plugin.get("runtimes", []))))

all_rff: set = set()
total_mtd_tools = 0
title_violations = []
missing_schema = []

for rt in plugin.get("runtimes", []):
    rff = rt.get("run_for_functions", [])
    all_rff.update(rff)
    mtd = rt.get("spec", {}).get("mcp_tool_description", {})
    tools = mtd.get("tools", [])
    total_mtd_tools += len(tools)
    for t in tools:
        schema = t.get("inputSchema", {})
        if "title" in schema:
            title_violations.append(t["name"])
        if not schema:
            missing_schema.append(t["name"])

check("all functions covered by run_for_functions",
      len(all_rff) == len(plugin.get("functions", [])),
      f"{len(all_rff)} vs {len(plugin.get('functions', []))}")
check("mcp_tool_description present on all runtimes",
      total_mtd_tools == 225, f"{total_mtd_tools} tools inlined")
check("no 'title' in inputSchema top-level (Copilot schema parser fix)",
      len(title_violations) == 0,
      f"{len(title_violations)} violations" if title_violations else "")
check("all tools have inputSchema",
      len(missing_schema) == 0,
      f"missing: {missing_schema[:3]}" if missing_schema else "")

# ── 3. declarativeAgent.json ──────────────────────────────────────────────────

print()
print("3. declarativeAgent.json")
da = json.loads(z.read("declarativeAgent.json"))
check("version is v1.5", da.get("version") == "v1.5", da.get("version"))
check("instructions present", bool(da.get("instructions")),
      f"{len(da.get('instructions',''))} chars")
check("no encoding corruption in instructions",
      "â€”" not in da.get("instructions", "") and
      "Ã°" not in da.get("instructions", ""))
check("actions references ai-plugin.json",
      any(a.get("file") == "ai-plugin.json" for a in da.get("actions", [])))

# ── 4. Live MCP server health ─────────────────────────────────────────────────

print()
print("4. Live MCP server health (via tunnel)")

tunnel_url = None
for rt in plugin.get("runtimes", []):
    url = rt.get("spec", {}).get("url", "")
    if "devtunnels.ms" in url:
        tunnel_url = url.rsplit("/", 2)[0]
        break

if not tunnel_url:
    print(f"  {WARN}  No devtunnel URL found in ai-plugin.json — skipping live tests")
else:
    print(f"  {INFO}  Tunnel base: {tunnel_url}")
    routes = [
        ("sf",      "sf__get_leads"),
        ("sn",      "sn__get_incidents"),
        ("sap",     "sap__get_purchase_orders"),
        ("hs",      "hs__get_contacts"),
        ("ft",      "ft__get_departures"),
        ("ds",      "ds__get_envelopes"),
        ("saphr",   "saphr__get_employee"),
        ("workday", "wday__get_worker"),
        ("coupa",   "coupa__get_invoices"),
        ("jira",    "jira__get_issues"),
    ]

    for prefix, sample_tool in routes:
        url = f"{tunnel_url}/{prefix}/mcp"
        try:
            r = httpx.post(
                url,
                json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
                      "params": {"protocolVersion": "2024-11-05",
                                 "capabilities": {},
                                 "clientInfo": {"name": "verify", "version": "1"}}},
                headers={"Accept": "application/json, text/event-stream",
                         "Content-Type": "application/json"},
                timeout=8,
            )
            sid = r.headers.get("mcp-session-id", "")
            body = r.text
            ok = '"protocolVersion"' in body and bool(sid)
            check(f"/{prefix}/mcp  initialize", ok,
                  f"HTTP {r.status_code}" + ("" if ok else f"  body={body[:80]}"))
        except Exception as exc:
            check(f"/{prefix}/mcp  initialize", False, str(exc)[:80])

# ── 5. End-to-end tool call ───────────────────────────────────────────────────

print()
print("5. End-to-end tool call  (sf__get_leads through tunnel)")

if tunnel_url:
    try:
        init_r = httpx.post(
            f"{tunnel_url}/sf/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
                  "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                             "clientInfo": {"name": "verify", "version": "1"}}},
            headers={"Accept": "application/json, text/event-stream",
                     "Content-Type": "application/json"},
            timeout=10,
        )
        sid = init_r.headers.get("mcp-session-id", "")
        httpx.post(
            f"{tunnel_url}/sf/mcp",
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            headers={"Accept": "application/json, text/event-stream",
                     "Content-Type": "application/json",
                     "mcp-session-id": sid},
            timeout=5,
        )
        call_r = httpx.post(
            f"{tunnel_url}/sf/mcp",
            json={"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                  "params": {"name": "sf__get_leads", "arguments": {}}},
            headers={"Accept": "application/json, text/event-stream",
                     "Content-Type": "application/json",
                     "mcp-session-id": sid},
            timeout=20,
        )
        body = call_r.text
        has_result = '"result"' in body and '"content"' in body
        is_error   = '"isError": true' in body or '"isError":true' in body
        check("sf__get_leads returned result", has_result,
              "error response" if is_error else ("no result" if not has_result else ""))
        if has_result and not is_error:
            # Extract first line of text content
            for line in body.split("\n"):
                if line.startswith("data:"):
                    obj = json.loads(line[5:])
                    text = obj.get("result", {}).get("content", [{}])[0].get("text", "")
                    print(f"       → {text[:100]}")
                    break
    except Exception as exc:
        check("sf__get_leads call", False, str(exc)[:80])

# ── Summary ───────────────────────────────────────────────────────────────────

print()
print("=" * 52)
if errors == 0:
    print(f"  \033[32mALL CHECKS PASSED\033[0m  — package is ready for Copilot")
else:
    print(f"  \033[31m{errors} CHECK(S) FAILED\033[0m  — fix before testing in Copilot")
print("=" * 52)
print()
sys.exit(0 if errors == 0 else 1)
