# agent/codegen.py
# This file does two things:
#   1. Try to pull out the HCL code block from LLM response
#   2. If LLM gives garbage output, fall back to the Jinja2 template for
#      whichever cloud provider was requested (templates/<provider>/main.tf.j2)

import re
import os
from jinja2 import Environment, FileSystemLoader
from agent.providers import PROVIDERS, validate_provider

TEMPLATES_ROOT = os.path.join(os.path.dirname(__file__), "..", "templates")


def extract_terraform_code(llm_output: str, provider: str, services: list,
                            requirements: str, app_name: str, vm_size: str = None) -> str:
    provider = validate_provider(provider)

    match = re.search(r"```(?:hcl|terraform)?\s*(.*?)```", llm_output, re.DOTALL)

    if match:
        code = match.group(1).strip()
        # basic sanity check - if it's less than 100 chars it's probably wrong
        if len(code) > 100:
            print(f"[Codegen] Extracted code from LLM output successfully ({provider})")
            return code

    # LLM output was empty or too short, use template instead
    print(f"[Codegen] LLM output not usable, using Jinja2 template fallback ({provider})")
    return render_template(provider, services, app_name, requirements, vm_size)


def render_template(provider: str, services: list, app_name: str, requirements: str,
                     vm_size: str = None) -> str:
    provider = validate_provider(provider)
    cfg = PROVIDERS[provider]
    vm_size = vm_size or cfg["default_vm_size"]

    provider_templates_dir = os.path.join(TEMPLATES_ROOT, provider)
    env = Environment(loader=FileSystemLoader(provider_templates_dir))

    context = {
        "app_name": app_name.lower().replace(" ", "-"),
        "region": cfg["default_region"],
        "requirements": requirements,
        "vm_size": vm_size,
    }

    # flags are named per-provider so templates read naturally, e.g. has_vm,
    # has_blob, has_sqldb ... built dynamically from the provider's service catalog
    for service_id in cfg["services"]:
        flag_name = f"has_{service_id.lower()}"
        context[flag_name] = service_id in services

    template = env.get_template("main.tf.j2")
    return template.render(**context)
