# Azure Serverless VNet API

This project provides a **serverless API** built on **Azure Functions (Python)** with a single HTTP function that can:
- Create a Virtual Network (VNet) with multiple subnets.
- Store metadata in **Cosmos DB**.
- Retrieve details of created VNets.
- Secure access with **Azure AD authentication** enabled directly in the Function App.

## 🚀 Features
- **Serverless**: Runs on Azure Functions with consumption-based scaling.
- **Networking**: Creates VNets and subnets using Azure Resource Manager SDK.
- **Storage**: Persists metadata in Cosmos DB.
- **Authentication**: Protected with Azure AD; all authenticated users can access.
- **Endpoints**:
  - `POST /api/vnets`** — Create Azure VNet with subnets (ARM via Managed Identity) and store summary in **Cosmos DB**
  - `GET /api/vnets/{name}?subscriptionId=&resourceGroupName=`** — Fetch stored summary from **Cosmos DB**

---

## 📦 Prerequisites
-  Azure subscription where you can create:
    - Resource Group, Storage Account, Function App (Python 3.10, Linux)
    - Cosmos DB (NoSQL) account + DB + Container
- Ability to assign **RBAC** roles to a **Managed Identity**
-  **Azure CLI** installed and logged in: `az login`
---

## 🛠️ Azure Portal Setup

### Step 1: Create Resource Group
- Portal → **Resource groups** → Create → Name: `vnet-api-rg`.

### Step 2: Create Storage Account
- Portal → **Storage accounts** → Create → Name: `vnetapistorage`.

### Step 3: Create Function App
- Portal → **Function App** → Create:
  - Runtime: Python 3.9+
  - Plan: Consumption
  - Storage: `vnetapistorage`

### Step 4: Create Cosmos DB
- Portal → **Azure Cosmos DB for NoSQL** → Create → Name: `vnetcosmos`.
- In **Data Explorer**:
  - Database: `VNetDB`
  - Container: `VNetContainer`
  - Partition key: `/id`

### Step 5: Enable Authentication
- Portal → **Function App → Authentication**.
- Add identity provider → Microsoft → Create new app registration .
- App Service authentication: On
- Unauthenticated requests: HTTP 401.
- Save.
- Where auth happens: Easy Auth enforces sign‑in before your Python function runs.
- Keep authLevel: "anonymous" in the trigger — the platform is the gatekeeper.

### Step 6: Enable Managed Identity
- Portal → **Function App → Identity** → System-assigned → **On** → Save.
- Assign RBAC roles:
  - **Contributor** (or Network Contributor) on Resource Group → to create VNets/subnets.
  - **Cosmos DB Account Contributor** → to write to Cosmos DB.

### Step 7: Configure App Settings
- Portal → **Function App → Configuration → Application settings**.
- Add:
  - `COSMOSDB_ACCOUNT_URI` — e.g., `https://<account>.documents.azure.com:443/`
  - `COSMOSDB_DB_NAME` — default `vnetdb`
  - `COSMOSDB_CONTAINER_NAME` — default `VnetRecords`
  - No Cosmos key is needed. The code uses Managed Identity via DefaultAzureCredential() and Cosmos DB RBAC.

### Step 8: Expose API and Get APP_URI
- Application ID URI of the App Registration that Azure automatically created when you enabled Authentication in your Function App.
- Portal → Function App → Authentication → Find Microsoft provider  → App Registration → Expose an API → Set API URI(if empty) → click set → This creates api://<CLIENT_ID> → Copy Application ID URI → This is your APP_URI → Use in CLI:APP_URI="api://<CLIENT_ID>"
  
## Security & Identity
- **Authentication**: Microsoft Entra ID via **App Service Authentication (Easy Auth)** → unauthenticated requests get **401**
- **ARM**: Function’s **Managed Identity** must have **Network Contributor** on the RG/subscription
- **Cosmos**: Function’s **Managed Identity** must have **Cosmos DB Built‑in Data Contributor** (data‑plane role) on the Cosmos account

## Deploy and test
# Deployment
- Step 1: Clone Repo
    - `git clone https://github.com/your-username/my-vnet-subnets-api.git`
    - `cd my-vnet-subnets-api`

- Step 2: Login to Azure
    - `az login`

- Step 3: Publish to Azure
    - `func azure functionapp publish vnet-api-func`
    - This uploads your code to the Function App. Azure installs dependencies and restarts the app.
 
# Test (curl or browser)
1. Get an access token (Azure CLI)
   - Token must be for your app registration audience (Application ID URI).
   - In most Easy Auth setups you’ll have an Application ID URI like api://<CLIENT_ID>.
   - `APP_URI="api://<YOUR_APP_CLIENT_ID>"`
   - `TOKEN=$(az account get-access-token --resource $APP_URI --query accessToken -o tsv)`
2. Create VNet (POST)
 ```curl -X POST "https://<FUNCTION_APP>.azurewebsites.net/api/vnets" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "subscriptionId": "<SUBSCRIPTION_ID>",
        "resourceGroupName": "<RG_FOR_VNET>",
        "vnetName": "vnet-demo-001",
        "location": "eastus",
        "addressSpace": ["10.10.0.0/16"],
        "subnets": [
          {"name": "apps", "addressPrefix": "10.10.1.0/24"},
          {"name": "db",   "addressPrefix": "10.10.2.0/24"}
        ]
      }'
```
3. Get VNet by name (GET)
 ```
  curl -H "Authorization: Bearer $TOKEN" "https://<FUNCTION_APP>.azurewebsites.net/api/vnets/vnet-demo-001?subscriptionId=<SUBSCRIPTION_ID>&resourceGroupName=<RG_FOR_VNET>"
```
4. Browser-only GET (prompts sign‑in once)
 ```
  https://<FUNCTION_APP>.azurewebsites.net/api/vnets/vnet-demo-001?subscriptionId=<SUBSCRIPTION_ID>&resourceGroupName=<RG_FOR_VNET>
```
# Validation 
- Check Cosmos DB → Data Explorer for metadata.
- Check Azure Portal → Virtual Networks for created VNets.
- Ensure unauthenticated requests fail with 401 Unauthorized.

# Notes
- Authentication is enforced by Function App Authentication.
- All authenticated users in your tenant can access the API.
