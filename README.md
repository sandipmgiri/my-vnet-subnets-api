# Azure Functions (Python) — VNet Create + Get (Cosmos DB, Entra ID Auth)

Endpoints:
- **POST `/api/vnets`** — Create Azure VNet with subnets (ARM via Managed Identity) and store summary in **Cosmos DB**
- **GET `/api/vnets/{name}?subscriptionId=&resourceGroupName=`** — Fetch stored summary from **Cosmos DB**

## Security & Identity
- **Authentication**: Microsoft Entra ID via **App Service Authentication (Easy Auth)** → unauthenticated requests get **401**
- **ARM**: Function’s **Managed Identity** must have **Network Contributor** on the RG/subscription
- **Cosmos**: Function’s **Managed Identity** must have **Cosmos DB Built‑in Data Contributor** (data‑plane role) on the Cosmos account

## App Settings
- `COSMOSDB_ACCOUNT_URI` — e.g., `https://<account>.documents.azure.com:443/`
- `COSMOSDB_DB_NAME` — default `vnetdb`
- `COSMOSDB_CONTAINER_NAME` — default `VnetRecords`

## Deploy (no local runtime needed)
```bash
az login
zip -r vnetapi.zip .
az functionapp deployment source config-zip \
  --resource-group <rg> \
  --name <functionapp> \
  --src vnetapi.zip
