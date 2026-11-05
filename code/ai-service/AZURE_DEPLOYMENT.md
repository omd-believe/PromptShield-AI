# Azure Deployment Guide for PromptShield AI Service

This document provides step-by-step instructions to deploy the **PromptShield AI Service** (FastAPI + LLMLingua-2 / spaCy) to Microsoft Azure.

---

## 1. Architecture & Resource Requirements

The AI microservice performs:
- **PII Detection & Anonymization** (spaCy NER + Regex)
- **Prompt Optimization & Compression** (LLMLingua-2 with deterministic fallback)
- **Safety, Constraint & Privacy Validation**

### Recommended Azure Compute Specs
- **CPU Deployment (Standard):** Minimum 2 vCPUs, 4 GB RAM (e.g., Azure Container Apps consumption plan, or App Service B2 / P1v3).
- **GPU Deployment (Accelerated):** Azure NC-series VM with NVIDIA T4 or A10 (e.g., `Standard_NC4as_T4_v3`).

---

## 2. Environment Variables Reference

Configure these in the Azure App Settings or Container App Environment:

| Variable | Recommended Value | Description |
| :--- | :--- | :--- |
| `AI_SERVICE_API_KEY` | *(Strong hex secret, e.g. 64 chars)* | Shared secret with Spring Boot backend (sent via `X-API-Key`) |
| `COMPRESSION_ENGINE` | `auto` | Engine selection: `auto`, `llmlingua`, or `deterministic` |
| `LLMLINGUA_ENABLED` | `true` | Enable LLMLingua-2 prompt compression |
| `LLMLINGUA_USE_ONLINE_DOWNLOAD` | `true` | Set `true` on initial deployment to download HuggingFace model weights |
| `LLMLINGUA_DEVICE` | `auto` | `auto` (uses CUDA if GPU present, else CPU), or force `cpu` / `cuda` |
| `LLMLINGUA_RATE` | `0.75` | Target token retention rate (0.75 = keep 75% tokens) |
| `LLMLINGUA_MAX_CONCURRENT_REQUESTS`| `1` | Semaphore limiting simultaneous inference to protect RAM/VRAM |
| `MAX_PROMPT_LENGTH` | `8000` | Max character length for input prompts |
| `SPACY_MODEL` | `en_core_web_sm` | spaCy NER model (bundled in Docker image) |
| `PORT` | `8000` | Port uvicorn binds to |

---

## 3. Option A: Deploy via Azure Container Apps (Recommended)

Azure Container Apps is serverless, cost-effective, and automatically provides a public HTTPS endpoint.

### Step 1: Login to Azure CLI
```bash
az login
az account set --subscription "<YOUR_SUBSCRIPTION_NAME_OR_ID>"
```

### Step 2: Create a Resource Group and Azure Container Registry (ACR)
```bash
# Set variables
RESOURCE_GROUP="rg-promptshield"
LOCATION="eastus"
ACR_NAME="promptshieldacr$RANDOM"
APP_NAME="promptshield-ai"

# Create Resource Group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create ACR (Basic SKU)
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic --admin-enabled true
```

### Step 3: Build and Push Docker Image to ACR
From the `ai-service` directory:
```bash
# Build image directly in Azure without needing local Docker
az acr build --registry $ACR_NAME --image promptshield-ai:latest .
```

### Step 4: Deploy Container App
```bash
# Retrieve ACR admin password
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

# Create Container App with 2.0 vCPU and 4.0 Gi RAM
az containerapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment "env-promptshield" \
  --image "$ACR_NAME.azurecr.io/promptshield-ai:latest" \
  --registry-server "$ACR_NAME.azurecr.io" \
  --registry-username $ACR_NAME \
  --registry-password "$ACR_PASSWORD" \
  --target-port 8000 \
  --ingress external \
  --cpu 2.0 \
  --memory 4.0Gi \
  --env-vars \
    AI_SERVICE_API_KEY="<YOUR_SECRET_KEY>" \
    COMPRESSION_ENGINE="auto" \
    LLMLINGUA_ENABLED="true" \
    LLMLINGUA_USE_ONLINE_DOWNLOAD="true" \
    LLMLINGUA_DEVICE="cpu"
```

Once deployed, the command outputs the public FQDN (e.g., `https://promptshield-ai.<random>.eastus.azurecontainerapps.io`).

---

## 4. Option B: Deploy to Azure App Service (Web App for Containers)

### Step 1: Create an App Service Plan (Linux)
```bash
az appservice plan create \
  --name "plan-promptshield" \
  --resource-group "rg-promptshield" \
  --is-linux \
  --sku B2
```

### Step 2: Create Web App from Container
```bash
az webapp create \
  --resource-group "rg-promptshield" \
  --plan "plan-promptshield" \
  --name "promptshield-ai" \
  --deployment-container-image-name "$ACR_NAME.azurecr.io/promptshield-ai:latest"
```

### Step 3: Configure Port and Environment Settings
```bash
az webapp config appsettings set \
  --resource-group "rg-promptshield" \
  --name "promptshield-ai" \
  --settings \
    WEBSITES_PORT="8000" \
    AI_SERVICE_API_KEY="<YOUR_SECRET_KEY>" \
    COMPRESSION_ENGINE="auto" \
    LLMLINGUA_ENABLED="true" \
    LLMLINGUA_USE_ONLINE_DOWNLOAD="true" \
    LLMLINGUA_DEVICE="cpu"
```

The service will be live at `https://promptshield-ai.azurewebsites.net`.

---

## 5. Verification & Testing

Verify the deployed Azure service:

```bash
# 1. Health check (should return {"status":"healthy"})
curl -i https://<YOUR_AZURE_URL>/health

# 2. Service identity
curl -i https://<YOUR_AZURE_URL>/

# 3. Privacy analysis endpoint (requires API key)
curl -X POST https://<YOUR_AZURE_URL>/analyze \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <YOUR_SECRET_KEY>" \
  -d '{"prompt": "Hello John Doe, my phone is 9876543210."}'
```

---

## 6. Connecting Spring Boot Backend to Azure

In the Spring Boot backend (Render or local), update the environment variables:

```properties
AI_SERVICE_URL=https://<YOUR_AZURE_URL>
AI_SERVICE_API_KEY=<YOUR_SECRET_KEY>
```
No code changes are required. Spring Boot will automatically route all optimization and analysis requests to the Azure-hosted FastAPI service with the proper authentication headers.

