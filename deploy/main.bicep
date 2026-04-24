// ══════════════════════════════════════════════════════════════════════════════
// GTC — Azure Container Apps Infrastructure
//
// Deploys: ACR, Log Analytics workspace, Container Apps environment,
//          managed identity (AcrPull), and the gtc-gateway Container App.
//
// The gateway image contains all 10 LOB MCP servers in one process.
// Individual LOB containers are not needed; the gateway handles all routing.
//
// Deploy:
//   az deployment group create \
//     --resource-group gtc-rg \
//     --template-file deploy/main.bicep \
//     --parameters @deploy/parameters.bicepparam
// ══════════════════════════════════════════════════════════════════════════════

@description('Azure region. Defaults to the resource group location.')
param location string = resourceGroup().location

@description('Container Apps Environment name')
param environmentName string = 'gtc-env'

@description('Azure Container Registry name (must be globally unique, 5-50 lowercase alphanumeric)')
param acrName string = 'gtcregistry'

@description('Container image tag to deploy')
param imageTag string = 'latest'

@description('Log Analytics retention in days')
param logRetentionDays int = 30

// ── Salesforce ─────────────────────────────────────────────────────────────────
@secure()
param sfInstanceUrl string = ''
@secure()
param sfClientId string = ''
@secure()
param sfClientSecret string = ''

// ── ServiceNow ─────────────────────────────────────────────────────────────────
param servicenowInstance string = ''         // e.g. dev12345 (not a secret)
param servicenowAuthMode string = 'oauth'    // oauth | basic
@secure()
param servicenowClientId string = ''
@secure()
param servicenowClientSecret string = ''
@secure()
param servicenowUsername string = ''
@secure()
param servicenowPassword string = ''

// ── SAP S/4HANA ────────────────────────────────────────────────────────────────
param sapMode string = 'sandbox'             // sandbox | tenant
@secure()
param sapApiKey string = ''
@secure()
param sapTenantUrl string = ''
@secure()
param sapUsername string = ''
@secure()
param sapPassword string = ''

// ── HubSpot ────────────────────────────────────────────────────────────────────
@secure()
param hubspotAccessToken string = ''

// ── Flight Tracker (OpenSky) ───────────────────────────────────────────────────
@secure()
param openskyClientId string = ''
@secure()
param openskyClientSecret string = ''

// ── DocuSign eSignature ────────────────────────────────────────────────────────
@secure()
param docusignIntegrationKey string = ''
@secure()
param docusignUserId string = ''
@secure()
param docusignAccountId string = ''
@secure()
param docusignRsaPrivateKey string = ''       // base64-encoded PEM
param docusignAuthServer string = 'account-d.docusign.com'
param docusignBaseUrl string = 'https://demo.docusign.net/restapi'

// ── SAP SuccessFactors HR ──────────────────────────────────────────────────────
@secure()
param sapSfOdataUrl string = ''
@secure()
param sapSfTokenUrl string = ''
@secure()
param sapSfCompanyId string = ''
@secure()
param sapSfClientId string = ''
@secure()
param sapSfResourceUri string = ''

// ── Workday ────────────────────────────────────────────────────────────────────
@secure()
param workdayBaseUrl string = ''
param workdayTenant string = ''
param workdaySkillsReport string = 'svasireddy/ESSMCPSkills'
param workdayLearningReport string = 'svasireddy/Required_Learning'

// ── Coupa Procurement ──────────────────────────────────────────────────────────
param coupaInstanceUrl string = 'https://mock.coupahost.com'
param coupaMock string = 'true'

// ── Jira Project Management ────────────────────────────────────────────────────
@secure()
param jiraBaseUrl string = ''
param jiraProjectKey string = ''

// ═════════════════════════════════════════════════════════════════════════════
// Core Infrastructure
// ═════════════════════════════════════════════════════════════════════════════

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }
}

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${environmentName}-logs'
  location: location
  properties: {
    retentionInDays: logRetentionDays
    sku: { name: 'PerGB2018' }
  }
}

resource cae 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${environmentName}-identity'
  location: location
}

// AcrPull role on the registry for the managed identity
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
resource acrPullAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, identity.id, acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// Gateway Container App (single container, all 10 LOBs in-process)
// ═════════════════════════════════════════════════════════════════════════════

var acrServer = acr.properties.loginServer

resource caGateway 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'gtc-gateway'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identity.id}': {} }
  }
  properties: {
    environmentId: cae.id
    configuration: {
      registries: [{
        server: acrServer
        identity: identity.id
      }]
      ingress: {
        external: true
        targetPort: 8080
        transport: 'http'
        corsPolicy: {
          allowedOrigins: ['*']
          allowedHeaders: ['*']
          allowedMethods: ['GET', 'POST', 'OPTIONS']
          allowCredentials: false
        }
      }
      secrets: [
        // Salesforce
        { name: 'sf-instance-url',            value: sfInstanceUrl }
        { name: 'sf-client-id',               value: sfClientId }
        { name: 'sf-client-secret',           value: sfClientSecret }
        // ServiceNow
        { name: 'sn-client-id',               value: servicenowClientId }
        { name: 'sn-client-secret',           value: servicenowClientSecret }
        { name: 'sn-username',                value: servicenowUsername }
        { name: 'sn-password',                value: servicenowPassword }
        // SAP S/4HANA
        { name: 'sap-api-key',                value: sapApiKey }
        { name: 'sap-tenant-url',             value: sapTenantUrl }
        { name: 'sap-username',               value: sapUsername }
        { name: 'sap-password',               value: sapPassword }
        // HubSpot
        { name: 'hubspot-access-token',       value: hubspotAccessToken }
        // Flight
        { name: 'opensky-client-id',          value: openskyClientId }
        { name: 'opensky-client-secret',      value: openskyClientSecret }
        // DocuSign
        { name: 'ds-integration-key',         value: docusignIntegrationKey }
        { name: 'ds-user-id',                 value: docusignUserId }
        { name: 'ds-account-id',              value: docusignAccountId }
        { name: 'ds-rsa-key',                 value: docusignRsaPrivateKey }
        // SAP SuccessFactors HR
        { name: 'sapsf-odata-url',            value: sapSfOdataUrl }
        { name: 'sapsf-token-url',            value: sapSfTokenUrl }
        { name: 'sapsf-company-id',           value: sapSfCompanyId }
        { name: 'sapsf-client-id',            value: sapSfClientId }
        { name: 'sapsf-resource-uri',         value: sapSfResourceUri }
        // Workday
        { name: 'workday-base-url',           value: workdayBaseUrl }
        // Jira
        { name: 'jira-base-url',              value: jiraBaseUrl }
      ]
    }
    template: {
      containers: [{
        name: 'gateway'
        image: '${acrServer}/gtc/gateway:${imageTag}'
        resources: { cpu: '1.0', memory: '2Gi' }
        env: [
          // Salesforce
          { name: 'SF_INSTANCE_URL',            secretRef: 'sf-instance-url' }
          { name: 'SF_CLIENT_ID',               secretRef: 'sf-client-id' }
          { name: 'SF_CLIENT_SECRET',           secretRef: 'sf-client-secret' }
          // ServiceNow
          { name: 'SERVICENOW_INSTANCE',        value: servicenowInstance }
          { name: 'SERVICENOW_AUTH_MODE',       value: servicenowAuthMode }
          { name: 'SERVICENOW_CLIENT_ID',       secretRef: 'sn-client-id' }
          { name: 'SERVICENOW_CLIENT_SECRET',   secretRef: 'sn-client-secret' }
          { name: 'SERVICENOW_USERNAME',        secretRef: 'sn-username' }
          { name: 'SERVICENOW_PASSWORD',        secretRef: 'sn-password' }
          // SAP S/4HANA
          { name: 'SAP_MODE',                   value: sapMode }
          { name: 'SAP_API_KEY',                secretRef: 'sap-api-key' }
          { name: 'SAP_TENANT_URL',             secretRef: 'sap-tenant-url' }
          { name: 'SAP_USERNAME',               secretRef: 'sap-username' }
          { name: 'SAP_PASSWORD',               secretRef: 'sap-password' }
          // HubSpot
          { name: 'HUBSPOT_ACCESS_TOKEN',       secretRef: 'hubspot-access-token' }
          // Flight
          { name: 'OPENSKY_CLIENT_ID',          secretRef: 'opensky-client-id' }
          { name: 'OPENSKY_CLIENT_SECRET',      secretRef: 'opensky-client-secret' }
          // DocuSign
          { name: 'DOCUSIGN_INTEGRATION_KEY',   secretRef: 'ds-integration-key' }
          { name: 'DOCUSIGN_USER_ID',           secretRef: 'ds-user-id' }
          { name: 'DOCUSIGN_ACCOUNT_ID',        secretRef: 'ds-account-id' }
          { name: 'DOCUSIGN_RSA_PRIVATE_KEY',   secretRef: 'ds-rsa-key' }
          { name: 'DOCUSIGN_AUTH_SERVER',       value: docusignAuthServer }
          { name: 'DOCUSIGN_BASE_URL',          value: docusignBaseUrl }
          // SAP SuccessFactors HR
          { name: 'SAP_SF_ODATA_URL',           secretRef: 'sapsf-odata-url' }
          { name: 'SAP_SF_TOKEN_URL',           secretRef: 'sapsf-token-url' }
          { name: 'SAP_SF_COMPANY_ID',          secretRef: 'sapsf-company-id' }
          { name: 'SAP_SF_CLIENT_ID',           secretRef: 'sapsf-client-id' }
          { name: 'SAP_SF_RESOURCE_URI',        secretRef: 'sapsf-resource-uri' }
          // Workday
          { name: 'WORKDAY_BASE_URL',           secretRef: 'workday-base-url' }
          { name: 'WORKDAY_TENANT',             value: workdayTenant }
          { name: 'WORKDAY_SKILLS_REPORT',      value: workdaySkillsReport }
          { name: 'WORKDAY_LEARNING_REPORT',    value: workdayLearningReport }
          // Coupa
          { name: 'COUPA_INSTANCE_URL',         value: coupaInstanceUrl }
          { name: 'COUPA_MOCK',                 value: coupaMock }
          // Jira
          { name: 'JIRA_BASE_URL',              secretRef: 'jira-base-url' }
          { name: 'JIRA_PROJECT_KEY',           value: jiraProjectKey }
          // Gateway
          { name: 'GATEWAY_PORT',               value: '8080' }
        ]
      }]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// Outputs
// ═════════════════════════════════════════════════════════════════════════════

@description('Public HTTPS URL of the GTC gateway — update MCP_GATEWAY_URL in regen_manifests.py')
output gatewayUrl string = 'https://${caGateway.properties.configuration.ingress.fqdn}'

@description('ACR login server for az acr build --registry')
output acrLoginServer string = acrServer

@description('Container Apps Environment resource ID')
output caeResourceId string = cae.id
