# agent/planner.py
# Builds the prompt that gets sent to the LLM.
# Now provider-aware: AWS / Azure / GCP each get their own Terraform
# provider block, resource naming conventions, and vocabulary so the
# LLM doesn't accidentally mix "aws_instance" into an Azure request.

from agent.providers import PROVIDERS, validate_provider

TERRAFORM_PROVIDER_HINT = {
    "aws": (
        'Use the "hashicorp/aws" provider (~> 5.0). Resource prefixes look like '
        'aws_instance, aws_s3_bucket, aws_db_instance, aws_vpc, aws_lambda_function, '
        'aws_eks_cluster, aws_cloudwatch_log_group, aws_iam_user.'
    ),
    "azure": (
        'Use the "hashicorp/azurerm" provider (~> 3.0) with features {} block, plus an '
        '"azurerm_resource_group" that every resource lives inside. Resource prefixes look '
        'like azurerm_linux_virtual_machine, azurerm_storage_account, azurerm_mssql_server, '
        'azurerm_mssql_database, azurerm_virtual_network, azurerm_linux_function_app, '
        'azurerm_kubernetes_cluster, azurerm_monitor_action_group, azurerm_role_assignment.'
    ),
    "gcp": (
        'Use the "hashicorp/google" provider (~> 5.0) with a "project" variable. Resource '
        'prefixes look like google_compute_instance, google_storage_bucket, '
        'google_sql_database_instance, google_compute_network, google_cloudfunctions2_function, '
        'google_container_cluster, google_monitoring_notification_channel, google_project_iam_member.'
    ),
}


def build_prompt(provider: str, services: list, requirements: str, app_name: str,
                  vm_size: str = None) -> str:
    provider = validate_provider(provider)
    cfg = PROVIDERS[provider]
    region = cfg["default_region"]
    vm_size = vm_size or cfg["default_vm_size"]

    services_str = ", ".join(services)

    vm_note = ""
    if cfg["vm_service"] in services:
        vm_note = f"\n- For the virtual machine/compute service, use size/type = \"{vm_size}\" exactly as given"

    prompt = f"""You are a Terraform expert. Generate production-ready Terraform HCL code for {cfg['label']}.

APPLICATION NAME: {app_name}
CLOUD PROVIDER: {cfg['label']}
SERVICES TO CREATE: {services_str}
REQUIREMENTS: {requirements}

RULES:
- {TERRAFORM_PROVIDER_HINT[provider]}
- {cfg['region_label']} should be "{region}"{vm_note}
- Tag/label every resource with Project="{app_name}", ManagedBy="terraform" (use the native tagging
  mechanism for {cfg['label']}: AWS tags, Azure tags, or GCP labels)
- Include output blocks for important values like public IPs, storage names, endpoints
- Keep the code simple and readable

OUTPUT FORMAT:
Only return the Terraform HCL code inside ```hcl and ``` markers.
Do not write any explanation before or after the code.

```hcl
# write your terraform code here
```"""

    return prompt
