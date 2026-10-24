# Azure + GitHub Actions Setup Guide

This guide sets up OIDC-based Azure authentication so GitHub Actions can run
`terraform apply` on your Azure subscription **without storing any client secrets**.

---

## Step 1 — Create an App Registration (Entra ID)

1. Azure Portal → **Microsoft Entra ID → App registrations → New registration**
2. Name it e.g. `github-actions-infra-agent`, leave everything else default
3. After creation, note down:
   - **Application (client) ID**
   - **Directory (tenant) ID**

---

## Step 2 — Add a Federated Credential (this replaces a client secret)

1. Open the App Registration → **Certificates & secrets → Federated credentials → Add credential**
2. Scenario: **GitHub Actions deploying Azure resources**
3. Fill in:
   - **Organization:** your GitHub username/org
   - **Repository:** the repo name InfraAgent creates (or use a wildcard pattern per-repo)
   - **Entity type:** Branch
   - **Branch name:** `main`
4. Save

---

## Step 3 — Assign the App a Role on your Subscription

1. Azure Portal → **Subscriptions → your subscription → Access control (IAM) → Add role assignment**
2. Role: **Contributor** (or a narrower custom role for production)
3. Assign access to: the App Registration from Step 1
4. Note down your **Subscription ID** (Subscriptions page)

---

## Step 4 — Add Secrets to Each GitHub Repo

After InfraAgent creates a repo, these secrets are set **automatically** by InfraAgent
if present in your local `.env`:

| Secret name             | Value                                   |
|--------------------------|------------------------------------------|
| `AZURE_CLIENT_ID`        | App registration's Application ID       |
| `AZURE_TENANT_ID`        | Directory (tenant) ID                   |
| `AZURE_SUBSCRIPTION_ID`  | Your subscription ID                    |

Add these to your local `infra-agent/.env`:

```
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_SUBSCRIPTION_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

---

## Step 5 — Verify in Azure

After the workflow completes, check:
- **Portal → Resource groups → `<app-name>-rg`**
- All resources are tagged `Project=<app-name>`, `ManagedBy=terraform`

---

## Troubleshooting

**Error: `AADSTS70021: No matching federated identity record found`**
→ The federated credential's branch/repo pattern doesn't match. Recheck Step 2.

**Error: `terraform init` can't find backend storage account**
→ The `azurerm` backend in `main.tf` expects a pre-existing resource group +
storage account for state. Either create those manually once, or (simpler for
a first run) delete the `backend "azurerm" {}` block and let Terraform use
local state — same pattern InfraAgent already uses for AWS via `backend_override.tf`.
