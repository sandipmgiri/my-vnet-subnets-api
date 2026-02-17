import os
import json
import logging
from typing import Dict, Any, Optional

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.models import VirtualNetwork, AddressSpace, Subnet
from azure.cosmos import CosmosClient, exceptions

# -----------------------------
# App Settings (set in Portal → Function App → Configuration)
# -----------------------------
COSMOS_URI = os.environ.get("COSMOSDB_ACCOUNT_URI")          # e.g., https://<account>.documents.azure.com:443/
COSMOS_DB = os.environ.get("COSMOSDB_DB_NAME", "vnetdb")
COSMOS_CONTAINER = os.environ.get("COSMOSDB_CONTAINER_NAME", "VnetRecords")

# -----------------------------
# Clients (Managed Identity)
# -----------------------------
def get_cosmos_container():
    """Cosmos container using Managed Identity (AAD). DB and container must exist."""
    if not COSMOS_URI:
        raise RuntimeError("COSMOSDB_ACCOUNT_URI must be set in App Settings.")
    cred = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    client = CosmosClient(COSMOS_URI, credential=cred, consistency_level="Session")
    db = client.get_database_client(COSMOS_DB)
    return db.get_container_client(COSMOS_CONTAINER)

def get_network_client(subscription_id: str) -> NetworkManagementClient:
    """ARM client using the Function's Managed Identity."""
    cred = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    return NetworkManagementClient(cred, subscription_id)

def doc_id(resource_group: str, vnet_name: str) -> str:
    """Cosmos item id: unique per RG + VNet name."""
    return f"{resource_group}:{vnet_name}"

# -----------------------------
# HTTP Function
#   POST /api/vnets             → create VNet (ARM) + store summary (Cosmos)
#   GET  /api/vnets/{name}?subscriptionId=&resourceGroupName= → get stored summary
# -----------------------------
async def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("VNet API invoked")
    method = req.method.upper()
    name = req.route_params.get("name")  # present for GET /vnets/{name}

    # -------- GET by name (from Cosmos) --------
    if method == "GET":
        if not name:
            return func.HttpResponse(
                "Use /api/vnets/{name}?subscriptionId=&resourceGroupName=",
                status_code=400
            )

        subscription_id = req.params.get("subscriptionId")
        resource_group = req.params.get("resourceGroupName")
        if not (subscription_id and resource_group):
            return func.HttpResponse("Missing query params: subscriptionId, resourceGroupName", status_code=400)

        try:
            container = get_cosmos_container()
            item = container.read_item(item=doc_id(resource_group, name), partition_key=subscription_id)
            return func.HttpResponse(json.dumps(item, default=str), mimetype="application/json", status_code=200)
        except exceptions.CosmosResourceNotFoundError:
            return func.HttpResponse("Not found", status_code=404)
        except Exception as ex:
            logging.exception("GET failed")
            return func.HttpResponse(f"Error: {ex}", status_code=500)

    # -------- POST create VNet (ARM) + store summary (Cosmos) --------
    if method == "POST":
        try:
            body = req.get_json()
        except ValueError:
            return func.HttpResponse("Invalid JSON body", status_code=400)

        # minimal validation
        required = ["subscriptionId", "resourceGroupName", "vnetName", "location", "addressSpace", "subnets"]
        missing = [k for k in required if k not in body]
        if missing:
            return func.HttpResponse(f"Missing fields: {', '.join(missing)}", status_code=400)
        if not isinstance(body["addressSpace"], list):
            return func.HttpResponse("addressSpace must be a list of CIDRs", status_code=400)
        if not isinstance(body["subnets"], list) or not body["subnets"]:
            return func.HttpResponse("subnets must be a non-empty list", status_code=400)

        sid = body["subscriptionId"]
        rg = body["resourceGroupName"]
        vnet_name = body["vnetName"]
        location = body["location"]
        addr_space = body["addressSpace"]
        subnets = body["subnets"]

        try:
            # 1) Create VNet in Azure
            net = get_network_client(sid)
            subnet_models = [Subnet(name=s["name"], address_prefix=s["addressPrefix"]) for s in subnets]
            vnet_params = VirtualNetwork(
                location=location,
                address_space=AddressSpace(address_prefixes=addr_space),
                subnets=subnet_models
            )
            poller = net.virtual_networks.begin_create_or_update(rg, vnet_name, vnet_params)
            vnet = poller.result()

            # 2) Prepare and store summary in Cosmos
            summary = {
                "id": vnet.id,
                "name": vnet.name,
                "location": vnet.location,
                "etag": vnet.etag,
                "provisioningState": getattr(vnet, "provisioning_state", None) or getattr(vnet, "provisioningState", None),
                "addressSpace": {"addressPrefixes": vnet.address_space.address_prefixes if vnet.address_space else []},
                "subnets": [{"name": s.name, "addressPrefix": s.address_prefix} for s in (vnet.subnets or [])]
            }

            container = get_cosmos_container()
            doc = {
                "id": doc_id(rg, vnet.name),
                "subscriptionId": sid,               # partition key
                "resourceGroupName": rg,
                "vnetName": vnet.name,
                "vnetId": vnet.id,
                "location": vnet.location,
                "etag": vnet.etag,
                "provisioningState": summary["provisioningState"],
                "addressSpace": summary["addressSpace"],
                "subnets": summary["subnets"]
            }
            container.upsert_item(doc)

            return func.HttpResponse(
                json.dumps({"message": "VNet created", "vnet": summary, "stored": doc}, default=str),
                mimetype="application/json",
                status_code": 201
            )
        except Exception as ex:
            logging.exception("Create failed")
            return func.HttpResponse(f"Error creating VNet: {ex}", status_code=500)

    return func.HttpResponse("Method not allowed", status_code=405)
