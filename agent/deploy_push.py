# agent/deploy_push.py
# (renamed from github_push.py)
# Pushes generated Terraform to a new/existing GitHub repo and wires up a
# GitHub Actions workflow that authenticates to whichever cloud provider
# was selected, using OIDC — no long-lived cloud keys stored anywhere.

import os
import json
import time
import traceback

from github import Github, GithubException
from dotenv import load_dotenv

from agent.providers import validate_provider


def _creds():
    load_dotenv(override=True)
    return os.getenv("GITHUB_TOKEN", "").strip(), os.getenv("GITHUB_USERNAME", "").strip()


BACKEND_OVERRIDE = """\
# Disables remote backend so terraform init works in CI
# without needing the state bucket/storage account to exist first.
terraform {
  backend "local" {}
}
"""


# ── Per-provider auth step + required secrets ──────────────────────────────

def _aws_auth_step() -> str:
    return """\
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region:     ${{ secrets.AWS_REGION }}
"""


def _azure_auth_step() -> str:
    return """\
      - name: Azure Login (Service Principal)
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Export ARM env vars for Terraform
        run: |
          echo "ARM_CLIENT_ID=${{ secrets.AZURE_CLIENT_ID }}" >> $GITHUB_ENV
          echo "ARM_CLIENT_SECRET=${{ secrets.AZURE_CLIENT_SECRET }}" >> $GITHUB_ENV
          echo "ARM_TENANT_ID=${{ secrets.AZURE_TENANT_ID }}" >> $GITHUB_ENV
          echo "ARM_SUBSCRIPTION_ID=${{ secrets.AZURE_SUBSCRIPTION_ID }}" >> $GITHUB_ENV
"""


def _gcp_auth_step() -> str:
    return """\
      - name: Google Auth (Workload Identity Federation)
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }}
          service_account:            ${{ secrets.GCP_SERVICE_ACCOUNT }}

      - name: Export project env var for Terraform
        run: echo "GOOGLE_PROJECT=${{ secrets.GCP_PROJECT_ID }}" >> $GITHUB_ENV
"""


PROVIDER_AUTH_STEPS = {
    "aws":   _aws_auth_step,
    "azure": _azure_auth_step,
    "gcp":   _gcp_auth_step,
}

# secret_name -> .env var name to read the value from
PROVIDER_SECRETS = {
    "aws": {
        "AWS_ROLE_ARN": "AWS_ROLE_ARN",
        "AWS_REGION":   "AWS_REGION",
    },
    "azure": {
        "AZURE_CLIENT_ID":       "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET":   "AZURE_CLIENT_SECRET",
        "AZURE_TENANT_ID":       "AZURE_TENANT_ID",
        "AZURE_SUBSCRIPTION_ID": "AZURE_SUBSCRIPTION_ID",
    },
    "gcp": {
        "GCP_WORKLOAD_IDENTITY_PROVIDER": "GCP_WORKLOAD_IDENTITY_PROVIDER",
        "GCP_SERVICE_ACCOUNT":            "GCP_SERVICE_ACCOUNT",
        "GCP_PROJECT_ID":                 "GCP_PROJECT_ID",
    },
}


def _build_deploy_workflow(provider: str) -> str:
    auth_step = PROVIDER_AUTH_STEPS[provider]()
    return f"""\
name: Deploy Infrastructure ({provider.upper()})

on:
  push:
    branches: [main]

jobs:
  terraform:
    name: Terraform Apply ({provider.upper()})
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read

    steps:
      - name: Checkout
        uses: actions/checkout@v4

{auth_step}
      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.7.5"

      - name: Terraform Init
        run: terraform init

      - name: Terraform Validate
        run: terraform validate

      - name: Terraform Plan
        run: terraform plan -out=tfplan

      - name: Terraform Apply
        run: terraform apply -auto-approve tfplan
"""


def _get_sha(repo, path: str):
    try:
        f = repo.get_contents(path)
        return f.sha if not isinstance(f, list) else f[0].sha
    except GithubException as e:
        if e.status == 404:
            return None
        raise


def _upsert(repo, path: str, content: str, msg: str):
    sha = _get_sha(repo, path)
    if sha:
        print(f"[GitHub] Updating : {path}")
        repo.update_file(path=path, message=msg, content=content, sha=sha)
    else:
        print(f"[GitHub] Creating : {path}")
        repo.create_file(path=path, message=msg, content=content)


def _commit_all_files(repo, files: dict, message: str, branch: str = "main"):
    """
    Writes every {path: content} pair in ONE commit -> ONE push event.

    Why this matters: our GitHub Actions workflow triggers on every push to
    main. Pushing 4 files as 4 separate commits (the old _upsert-in-a-loop
    approach) fires 4 separate workflow runs on any repo that already has
    the workflow file from a prior deployment — each one racing to
    `terraform apply` the same infrastructure. A single commit means a
    single push means a single run, every time.
    """
    from github.InputGitTreeElement import InputGitTreeElement

    parents = []
    base_tree = None
    try:
        ref = repo.get_git_ref(f"heads/{branch}")
        base_commit = repo.get_git_commit(ref.object.sha)
        base_tree = base_commit.tree
        parents = [base_commit]
    except GithubException as e:
        # GitHub returns 409 "Git Repository is empty" for a brand new repo
        # with zero commits (not 404 as you might expect) — that's fine,
        # it just means this is the very first commit, no parent needed.
        if e.status not in (404, 409):
            raise

    # NOTE: pass `content=` directly instead of pre-creating blobs via
    # repo.create_git_blob() first. On a totally empty repo (zero commits),
    # the standalone /git/blobs endpoint returns 409 "Git Repository is
    # empty" — but /git/trees accepts inline `content` and creates the
    # blobs itself as part of the same request, which works fine even on
    # a brand new repo. This is the actual fix for that 409.
    tree_elements = [
        InputGitTreeElement(path=path, mode="100644", type="blob", content=content)
        for path, content in files.items()
    ]
    new_tree = repo.create_git_tree(tree_elements, base_tree) if base_tree is not None else repo.create_git_tree(tree_elements)
    new_commit = repo.create_git_commit(message, new_tree, parents)

    try:
        ref = repo.get_git_ref(f"heads/{branch}")
        ref.edit(new_commit.sha)
    except GithubException as e:
        if e.status in (404, 409):
            repo.create_git_ref(f"refs/heads/{branch}", new_commit.sha)
        else:
            raise

    print(f"[GitHub] \u2705 Committed {len(files)} files in a single push: {new_commit.sha[:7]}")


def _set_repo_secret(repo, secret_name: str, secret_value: str):
    try:
        # PyGitHub encrypts internally (fetches the repo's public key and
        # seals the value itself) — pass the plaintext value, not a
        # pre-encrypted one, and don't pass key_id positionally.
        repo.create_secret(secret_name, secret_value, secret_type="actions")
        print(f"[GitHub] \u2705 Secret set: {secret_name}")
    except Exception as e:
        print(f"[GitHub] \u26a0\ufe0f  Could not set secret {secret_name}: {e}")


def push_code_to_github(
    provider: str,
    terraform_code: str,
    request_id: int,
    requirements: str,
    app_name: str = "",
) -> str:
    provider = validate_provider(provider)
    load_dotenv(override=True)
    token, username = _creds()

    if not token or token.startswith("your_"):
        raise ValueError(
            "GITHUB_TOKEN missing in .env\n"
            "Get one at: https://github.com/settings/tokens\n"
            "Required scopes: repo + workflow"
        )

    g = Github(token)
    try:
        me = g.get_user()
        print(f"[GitHub] Authenticated as: {me.login}")
    except GithubException as e:
        raise ValueError(
            f"GitHub auth failed ({e.status}): {e.data.get('message', e.data)}"
        )

    safe_name = (app_name or "").lower().strip().replace(" ", "-").replace("_", "-")
    if not safe_name:
        safe_name = f"infra-request-{request_id}"
    # A new, uniquely-named repo is created for every run. This is safe now
    # because neither cloud's auth is tied to a specific repo name anymore:
    #   - AWS  uses an IAM trust policy with a StringLike wildcard
    #     (repo:<org>@<orgId>/*:ref:refs/heads/main) — matches any repo
    #   - Azure uses a Service Principal client secret (AZURE_CREDENTIALS)
    #     — not OIDC, so there's no per-repo federated credential at all
    #   - GCP   uses Workload Identity Federation with a wildcard binding
    #     (attribute.repository/<owner>/*) — also matches any repo
    # so every new repo automatically gets working credentials with zero
    # manual setup, and each deploy is fully isolated in its own repo.
    repo_name = f"{safe_name}-{provider}-infra-{request_id}"

    print(f"[GitHub] Repo name will be: {repo_name}")

    try:
        repo = me.create_repo(
            name=repo_name,
            description=f"{provider.upper()} Terraform infra for {app_name or requirements[:60]}",
            auto_init=True,   # bootstraps an initial commit — Git Data API 409s on a truly empty repo
            private=False,
        )
        print(f"[GitHub] Created repo: {repo.html_url}")
        time.sleep(2)  # give GitHub a moment to finish creating the initial commit/branch
    except GithubException as e:
        if e.status == 422:
            repo = me.get_repo(repo_name)
            print(f"[GitHub] Reusing existing repo: {repo.html_url}")
        else:
            raise

    # ── Push provider-specific secrets, read from .env ─────────────────────
    missing_secrets = []
    for secret_name, env_var in PROVIDER_SECRETS[provider].items():
        value = os.getenv(env_var, "").strip()
        if value:
            _set_repo_secret(repo, secret_name, value)
        else:
            missing_secrets.append(secret_name)

    if missing_secrets:
        print(f"[GitHub] \u26a0\ufe0f  Missing in .env, skipped: {missing_secrets}")

    # azure/login@v2 needs one combined JSON blob (the 'creds' input) for
    # Service Principal auth — it does not accept client-id/client-secret
    # as separate inputs. Build it from the same four values above.
    if provider == "azure" and not missing_secrets:
        azure_creds_json = json.dumps({
            "clientId":       os.getenv("AZURE_CLIENT_ID", "").strip(),
            "clientSecret":   os.getenv("AZURE_CLIENT_SECRET", "").strip(),
            "subscriptionId": os.getenv("AZURE_SUBSCRIPTION_ID", "").strip(),
            "tenantId":       os.getenv("AZURE_TENANT_ID", "").strip(),
        })
        _set_repo_secret(repo, "AZURE_CREDENTIALS", azure_creds_json)

    secret_names = list(PROVIDER_SECRETS[provider].keys())
    if provider == "azure":
        secret_names.append("AZURE_CREDENTIALS")
    secret_rows = "\n".join(
        f"| `{name}` | set automatically from .env |" for name in secret_names
    )

    auth_note = (
        f"This repo uses **OIDC** to authenticate with {provider.upper()} — no static keys stored anywhere."
        if provider != "azure" else
        "This repo authenticates to Azure using a **Service Principal client secret** "
        "(not OIDC) — the secret is encrypted at rest by GitHub and masked in all logs, "
        "but it is a long-lived credential, so rotate it periodically in Entra ID."
    )

    readme = (
        f"# {repo_name}\n\n"
        f"**Cloud:** {provider.upper()}\n"
        f"**App:** {app_name}\n"
        f"**Requirements:** {requirements}\n\n"
        "Auto-generated by [InfraAgent](https://github.com).\n\n"
        "## Authentication\n\n"
        f"{auth_note}\n\n"
        "Secrets are set automatically by InfraAgent:\n\n"
        "| Secret | Value |\n"
        "|--------|-------|\n"
        f"{secret_rows}\n\n"
        f"**Actions \u2192 Deploy Infrastructure ({provider.upper()}) \u2192 Re-run jobs** to redeploy.\n"
    )

    try:
        files = {
            "README.md":                    readme,
            "main.tf":                      terraform_code,
            "backend_override.tf":          BACKEND_OVERRIDE,
            f".github/workflows/deploy-{provider}.yml": _build_deploy_workflow(provider),
        }
        try:
            _commit_all_files(
                repo, files,
                f"deploy: {provider} infrastructure for {app_name or 'app'} (request #{request_id})",
            )
        except GithubException as e:
            if e.status in (403, 404) and "workflow" in str(e.data).lower():
                raise RuntimeError(
                    f"Could not push .github/workflows/deploy-{provider}.yml\n"
                    "Your token is missing the 'workflow' scope.\n\n"
                    "FIX:\n"
                    "  1. Go to https://github.com/settings/tokens\n"
                    "  2. Edit your infra-agent token\n"
                    "  3. Tick the 'workflow' checkbox\n"
                    "  4. Update token, copy new value\n"
                    "  5. Paste into .env as GITHUB_TOKEN=ghp_...\n"
                    "  6. Restart the backend\n\n"
                    "NOTE: nothing was pushed this run — the commit either succeeds\n"
                    "completely or not at all now, so main.tf can't be half-pushed."
                ) from e
            raise

    except GithubException as e:
        print(f"[GitHub] Push error {e.status}: {e.data}")
        traceback.print_exc()
        raise RuntimeError(
            f"GitHub push failed (HTTP {e.status}): {e.data.get('message', str(e.data))}"
        )

    print(f"[GitHub] \u2705 All files pushed in a single commit: {repo.html_url}")
    return repo.html_url