# Azure Serverless VNet API

This project provides a **serverless API** built on **Azure Functions (Python)** that can:
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
- Azure Subscription
- Azure CLI (`az login`)
- Python 3.9+
- Azure Functions Core Tools (`npm install -g azure-functions-core-tools@4`)
- Cosmos DB account (SQL API)

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
- Add identity provider → Microsoft.
- Require authentication → Allow all authenticated users.

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

## Security & Identity
- **Authentication**: Microsoft Entra ID via **App Service Authentication (Easy Auth)** → unauthenticated requests get **401**
- **ARM**: Function’s **Managed Identity** must have **Network Contributor** on the RG/subscription
- **Cosmos**: Function’s **Managed Identity** must have **Cosmos DB Built‑in Data Contributor** (data‑plane role) on the Cosmos account

## Deploy and test
# Deployment
- Step 1: Clone Repo
    - git clone https://github.com/your-username/my-vnet-subnets-api.git
    - cd my-vnet-subnets-api

- Step 2: Login to Azure
    - az login

- Step 3: Publish to Azure
    - func azure functionapp publish vnet-api-func
    - This uploads your code to the Function App. Azure installs dependencies and restarts the app.
 
# Test

# Validation 
- Check Cosmos DB → Data Explorer for metadata.
- Check Azure Portal → Virtual Networks for created VNets.
- Ensure unauthenticated requests fail with 401 Unauthorized.

# Notes
- Authentication is enforced by Function App Authentication.
- All authenticated users in your tenant can access the API.
