#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# GTC — Provision infrastructure + build + deploy to Azure Container Apps
#
# Prerequisites:
#   az login && az account set -s <subscription-id>
#   az bicep install  (or az bicep upgrade)
#
# Usage:
#   export RESOURCE_GROUP=gtc-rg
#   export LOCATION=eastus
#   export ACR_NAME=gtcregistry          # globally unique, lowercase
#   cp deploy/parameters.example.bicepparam deploy/parameters.bicepparam
#   # edit parameters.bicepparam with real credentials
#   bash deploy/deploy.sh
#
# Set IMAGE_TAG to override the container image tag (default: latest).
# Set SKIP_BUILD=1 to skip image builds (re-use existing tags in ACR).
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-gtc-rg}"
LOCATION="${LOCATION:-eastus}"
ACR_NAME="${ACR_NAME:-gtcregistry}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
PARAMS_FILE="${PARAMS_FILE:-deploy/parameters.bicepparam}"
SKIP_BUILD="${SKIP_BUILD:-0}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() { echo "[$(date +%H:%M:%S)] $*"; }

# ── Step 1: Resource group ────────────────────────────────────────────────────
log "Creating resource group '$RESOURCE_GROUP' in '$LOCATION' (idempotent)..."
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none

# ── Step 2: Bicep deployment ──────────────────────────────────────────────────
log "Deploying Bicep template (this may take ~3 min on first run)..."
DEPLOY_OUTPUT=$(az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file "$REPO_ROOT/deploy/main.bicep" \
  --parameters "@$REPO_ROOT/$PARAMS_FILE" \
  --parameters acrName="$ACR_NAME" imageTag="$IMAGE_TAG" \
  --output json)

GATEWAY_URL=$(echo "$DEPLOY_OUTPUT" | python3 -c \
  "import sys,json; o=json.load(sys.stdin); print(o['properties']['outputs']['gatewayUrl']['value'])")
ACR_SERVER=$(echo "$DEPLOY_OUTPUT" | python3 -c \
  "import sys,json; o=json.load(sys.stdin); print(o['properties']['outputs']['acrLoginServer']['value'])")

log "Gateway URL: $GATEWAY_URL"
log "ACR server:  $ACR_SERVER"

# ── Step 3: Remote image builds via az acr build (Task 15) ───────────────────
if [[ "$SKIP_BUILD" == "1" ]]; then
  log "SKIP_BUILD=1 — skipping image builds."
else
  log "Building container images in ACR (remote build — no Docker daemon needed)..."

  build() {
    local name="$1"
    local dockerfile="$2"
    local context="$3"
    log "  Building gtc/$name:$IMAGE_TAG ..."
    az acr build \
      --registry "$ACR_NAME" \
      --image "gtc/${name}:${IMAGE_TAG}" \
      --file "${REPO_ROOT}/${dockerfile}" \
      "${REPO_ROOT}/${context}" \
      --no-wait \
      --output none
  }

  # LOBs with self-contained Dockerfiles (build context = their own dir)
  build salesforce  "sf-mcp-app/Dockerfile"         "sf-mcp-app"
  build servicenow  "snow-mcp-app/Dockerfile"        "snow-mcp-app"
  build sap         "sap-mcp-app/Dockerfile"         "sap-mcp-app"
  build hubspot     "hubspot-mcp-app/Dockerfile"     "hubspot-mcp-app"
  build flight      "flight-mcp-app/Dockerfile"      "flight-mcp-app"
  build docusign    "docusign-mcp-app/Dockerfile"    "docusign-mcp-app"

  # LOBs that depend on shared-mcp-lib (build context = project root)
  build saphr       "saphr-mcp-app/Dockerfile"       "."
  build workday     "workday-mcp-app/Dockerfile"     "."
  build coupa       "coupa-mcp-app/Dockerfile"       "."
  build jira        "jira-mcp-app/Dockerfile"        "."

  # Gateway (also depends on all LOBs — context must be project root)
  build gateway     "gateway/Dockerfile"             "."

  log "Waiting for all ACR builds to complete..."
  az acr task list-runs \
    --registry "$ACR_NAME" \
    --output table \
    --query "[?status=='Running'].[runId,taskName,status,createTime]" 2>/dev/null || true

  # Poll until no running builds remain (max 20 min)
  TIMEOUT=1200
  ELAPSED=0
  while [[ $ELAPSED -lt $TIMEOUT ]]; do
    RUNNING=$(az acr task list-runs \
      --registry "$ACR_NAME" \
      --query "length([?status=='Running'])" \
      --output tsv 2>/dev/null || echo "0")
    if [[ "$RUNNING" == "0" ]]; then
      break
    fi
    log "  $RUNNING build(s) still running... (${ELAPSED}s elapsed)"
    sleep 30
    ELAPSED=$((ELAPSED + 30))
  done
  log "All ACR builds complete."
fi

# ── Step 4: Update container app with new image ───────────────────────────────
log "Updating gtc-gateway with image $ACR_SERVER/gtc/gateway:$IMAGE_TAG ..."
az containerapp update \
  --name "gtc-gateway" \
  --resource-group "$RESOURCE_GROUP" \
  --image "${ACR_SERVER}/gtc/gateway:${IMAGE_TAG}" \
  --output none

log "Deployment complete!"
log ""
log "  Gateway URL:  $GATEWAY_URL"
log ""
log "Next step — update regen_manifests.py:"
log "  export MCP_GATEWAY_URL=$GATEWAY_URL"
log "  python regen_manifests.py"
log ""
log "Or set permanently in a .env file:"
log "  echo 'MCP_GATEWAY_URL=$GATEWAY_URL' >> .env"
