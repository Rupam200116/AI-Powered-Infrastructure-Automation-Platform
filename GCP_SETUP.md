# GCP + GitHub Actions Setup Guide

This guide sets up Workload Identity Federation so GitHub Actions can run
`terraform apply` on your GCP project **without storing any service account keys**.

---

## Step 1 — Create a Workload Identity Pool + Provider

```bash
gcloud iam workload-identity-pools create "github-pool" \
  --location="global" \
  --display-name="GitHub Actions Pool"

gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Actions Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"
```

Note the full provider resource name, it looks like:
`projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/github-pool/providers/github-provider`

---

## Step 2 — Create a Service Account for Terraform

```bash
gcloud iam service-accounts create infra-agent-deployer \
  --display-name="InfraAgent Terraform Deployer"
```

Grant it a role on the project (Editor for testing, narrower roles for production):

```bash
gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:infra-agent-deployer@<PROJECT_ID>.iam.gserviceaccount.com" \
  --role="roles/editor"
```

---

## Step 3 — Allow GitHub Actions to Impersonate the Service Account

```bash
gcloud iam service-accounts add-iam-policy-binding \
  infra-agent-deployer@<PROJECT_ID>.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/github-pool/attribute.repository/YOUR_GITHUB_USERNAME/*"
```

---

## Step 4 — Add Secrets to Each GitHub Repo

After InfraAgent creates a repo, these secrets are set **automatically** by
InfraAgent if present in your local `.env`:

| Secret name                        | Value                                                                                          |
|--------------------------------------|--------------------------------------------------------------------------------------------------|
| `GCP_WORKLOAD_IDENTITY_PROVIDER`   | `projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |
| `GCP_SERVICE_ACCOUNT`              | `infra-agent-deployer@<PROJECT_ID>.iam.gserviceaccount.com`                                     |
| `GCP_PROJECT_ID`                   | `<PROJECT_ID>`                                                                                    |

Add these to your local `infra-agent/.env`:

```
GCP_WORKLOAD_IDENTITY_PROVIDER=projects/1234567890/locations/global/workloadIdentityPools/github-pool/providers/github-provider
GCP_SERVICE_ACCOUNT=infra-agent-deployer@my-project.iam.gserviceaccount.com
GCP_PROJECT_ID=my-project
```

---

## Step 5 — Verify in GCP

After the workflow completes, check:
- **Console → Compute Engine / Cloud Storage / Cloud SQL / GKE** for the created resources
- All resources are labeled `project=<app-name>`

---

## Troubleshooting

**Error: `permission denied on resource (or it may not exist)`**
→ The service account is missing the IAM role from Step 2, or the binding in Step 3 doesn't match your repo.

**Error: `terraform init` can't find GCS backend bucket**
→ The `gcs` backend in `main.tf` expects a pre-existing state bucket. Create it once with
`gsutil mb gs://<app-name>-tf-state`, or delete the `backend "gcs" {}` block for local state
(same pattern as `backend_override.tf` already does for AWS).
