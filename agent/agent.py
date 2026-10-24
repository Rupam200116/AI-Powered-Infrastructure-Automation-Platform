# agent/agent.py
import os
import requests
from dotenv import load_dotenv
from agent.planner import build_prompt
from agent.codegen import extract_terraform_code
from agent.validator import run_terraform_plan
from agent.cost import run_infracost
from agent.deploy_push import push_code_to_github

load_dotenv()
OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "codellama:7b")


class InfraAgent:

    def generate_terraform(self, provider, services, requirements, app_name, vm_size=None):
        prompt = build_prompt(provider, services, requirements, app_name, vm_size)
        print(f"[Agent] Sending prompt to Ollama for {provider} services: {services}")
        try:
            resp = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
                      "options": {"num_predict": 512, "temperature": 0.1}},
                timeout=(10, 60)
            )
            resp.raise_for_status()
            llm_output = resp.json().get("response", "")
            print(f"[Agent] Got response from Ollama ({len(llm_output)} chars)")
        except Exception as e:
            print(f"[Agent] Ollama error: {e}, falling back to template")
            llm_output = ""
        code = extract_terraform_code(llm_output, provider, services, requirements, app_name, vm_size)
        print(f"[Agent] Terraform code ready ({len(code)} chars)")
        return code

    def run_plan(self, terraform_code, request_id):
        print(f"[Agent] Running terraform plan for request #{request_id}")
        return run_terraform_plan(terraform_code, request_id)

    def estimate_cost(self, terraform_code, request_id):
        print(f"[Agent] Estimating cost for request #{request_id}")
        return run_infracost(terraform_code, request_id)

    def push_to_github(self, provider, terraform_code, request_id, requirements, app_name=""):
        print(f"[Agent] Pushing {provider} code to GitHub for request #{request_id}")
        return push_code_to_github(provider, terraform_code, request_id, requirements, app_name)
