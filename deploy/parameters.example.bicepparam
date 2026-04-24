// GTC — Azure Container Apps deployment parameters
//
// Copy this file to parameters.bicepparam and fill in real values.
// parameters.bicepparam is .gitignored — never commit credentials.
//
// Usage:
//   cp deploy/parameters.example.bicepparam deploy/parameters.bicepparam
//   # edit parameters.bicepparam
//   bash deploy/deploy.sh

using './main.bicep'

// ── Infrastructure ────────────────────────────────────────────────────────────
param environmentName = 'gtc-env'
param acrName         = 'gtcregistry'    // must be globally unique (5-50 lowercase alphanum)
param location        = 'eastus'
param imageTag        = 'latest'
param logRetentionDays = 30

// ── Salesforce ─────────────────────────────────────────────────────────────────
param sfInstanceUrl   = ''               // https://your-org.salesforce.com
param sfClientId      = ''
param sfClientSecret  = ''

// ── ServiceNow ─────────────────────────────────────────────────────────────────
param servicenowInstance   = ''          // e.g. dev12345  (no https://)
param servicenowAuthMode   = 'oauth'     // oauth | basic
param servicenowClientId   = ''
param servicenowClientSecret = ''
param servicenowUsername   = ''          // only for basic auth
param servicenowPassword   = ''          // only for basic auth

// ── SAP S/4HANA ────────────────────────────────────────────────────────────────
param sapMode       = 'sandbox'          // sandbox | tenant
param sapApiKey     = ''                 // SAP API Business Hub API key (sandbox)
param sapTenantUrl  = ''                 // https://my-tenant.s4hana.ondemand.com
param sapUsername   = ''                 // for tenant mode
param sapPassword   = ''                 // for tenant mode

// ── HubSpot ────────────────────────────────────────────────────────────────────
param hubspotAccessToken = ''            // Private App token

// ── Flight Tracker (OpenSky) ───────────────────────────────────────────────────
param openskyClientId     = ''           // leave blank for anonymous (rate-limited)
param openskyClientSecret = ''

// ── DocuSign eSignature ────────────────────────────────────────────────────────
param docusignIntegrationKey = ''
param docusignUserId         = ''        // GUID
param docusignAccountId      = ''        // GUID
param docusignRsaPrivateKey  = ''        // base64(PEM) — use: base64 -w0 rsa_key.pem
param docusignAuthServer     = 'account-d.docusign.com'   // demo; prod: account.docusign.com
param docusignBaseUrl        = 'https://demo.docusign.net/restapi'

// ── SAP SuccessFactors HR ──────────────────────────────────────────────────────
param sapSfOdataUrl    = ''              // https://api4.successfactors.com/odata/v2/
param sapSfTokenUrl    = ''
param sapSfCompanyId   = ''
param sapSfClientId    = ''
param sapSfResourceUri = ''

// ── Workday ────────────────────────────────────────────────────────────────────
param workdayBaseUrl       = ''          // https://wd2-impl-services1.workday.com/...
param workdayTenant        = ''
param workdaySkillsReport  = 'svasireddy/ESSMCPSkills'
param workdayLearningReport = 'svasireddy/Required_Learning'

// ── Coupa Procurement ──────────────────────────────────────────────────────────
param coupaInstanceUrl = 'https://mock.coupahost.com'
param coupaMock        = 'true'          // set to 'false' for live tenant

// ── Jira Project Management ────────────────────────────────────────────────────
param jiraBaseUrl    = ''                // https://your-org.atlassian.net
param jiraProjectKey = ''               // e.g. GTC
