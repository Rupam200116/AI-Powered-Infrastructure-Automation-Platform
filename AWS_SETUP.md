# AWS + GitHub Actions Setup Guide

This guide sets up OIDC-based AWS authentication so GitHub Actions can run
`terraform apply` on your AWS account **without storing any AWS keys anywhere**.

---

## Step 1 — Create an IAM OIDC Identity Provider in AWS

1. Open **AWS Console → IAM → Identity providers → Add provider**
2. Choose **OpenID Connect**
3. Fill in:
   - **Provider URL:** `https://token.actions.githubusercontent.com`
   - **Audience:** `sts.amazonaws.com`
4. Click **Add provider**

---

## Step 2 — Create an IAM Role for GitHub Actions

1. Go to **IAM → Roles → Create role**
2. Select **Web identity**
3. Choose:
   - **Identity provider:** `token.actions.githubusercontent.com`
   - **Audience:** `sts.amazonaws.com`
4. Click **Next** and attach these policies:
   - `AmazonEC2FullAccess`
   - `AmazonS3FullAccess`
   - `AmazonRDSFullAccess`
   - `AmazonVPCFullAccess`
   - `IAMFullAccess`
   - `AmazonEKSClusterPolicy`
   - `CloudWatchFullAccess`
   *(Or use `AdministratorAccess` for testing — restrict later for production)*
5. Name the role: `GitHubActionsRole`
6. Click **Create role**
7. Open the role, go to **Trust relationships → Edit trust policy**
8. Replace the condition block with:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<YOUR_ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_USERNAME/*:ref:refs/heads/main"
        },
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        }
      }
    }
  ]
}
```

Replace `<YOUR_ACCOUNT_ID>` with your 12-digit AWS account ID and
`YOUR_GITHUB_USERNAME` with your GitHub username (e.g. `Rupam200116`).

9. Copy the **Role ARN** — it looks like:
   `arn:aws:iam::123456789012:role/GitHubActionsRole`

---

## Step 3 — Add Secrets to Each GitHub Repo

After InfraAgent creates a repo, open it on GitHub and go to:
**Settings → Secrets and variables → Actions → New repository secret**

Add these two secrets:

| Secret name    | Value                                              |
|----------------|----------------------------------------------------|
| `AWS_ROLE_ARN` | `arn:aws:iam::123456789012:role/GitHubActionsRole` |
| `AWS_REGION`   | `ap-south-1`                                       |

---

## Step 4 — Trigger the Deployment

Once secrets are set, the workflow already ran on the initial push (when the
repo was created). To re-trigger it:

1. Go to the repo on GitHub
2. Click **Actions → Deploy Infrastructure**
3. Click **Re-run all jobs**

Or push any small change to `main.tf` to trigger a new run.

---

## Step 5 — Verify in AWS

After the workflow completes:
- **EC2**: AWS Console → EC2 → Instances
- **S3**: AWS Console → S3 → Buckets
- **RDS**: AWS Console → RDS → Databases
- **VPC**: AWS Console → VPC → Your VPCs

All resources will have tags: `Project=<app-name>`, `ManagedBy=terraform`

---

## Troubleshooting

**Error: `is not authorized to perform: sts:AssumeRoleWithWebIdentity`**
→ Check the trust policy condition — the `sub` claim must match your GitHub username/repo pattern.

**Error: `Could not load credentials from any providers`**
→ The `AWS_ROLE_ARN` secret is missing or wrong in the repo.

**Terraform state issues (concurrent runs)**
→ The generated `main.tf` uses a local backend by default. For team use, change to S3 backend and enable state locking with DynamoDB.
