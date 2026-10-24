# backend/workflow.py
import asyncio
import sqlite3
from datetime import datetime
from agent.agent import InfraAgent


def update_status(request_id: int, status: str, **extra_fields):
    db = sqlite3.connect("requests.db")
    set_parts = ["status=?", "updated_at=?"]
    values    = [status, datetime.now().isoformat()]
    for field, value in extra_fields.items():
        set_parts.append(f"{field}=?")
        values.append(value)
    values.append(request_id)
    db.execute(f"UPDATE requests SET {', '.join(set_parts)} WHERE id=?", values)
    db.commit()
    db.close()


class WorkflowEngine:

    def __init__(self):
        self.agent = InfraAgent()

    async def run(self, request_id: int, cloud_provider: str, services: list, requirements: str,
                  app_name: str, vm_size: str = None) -> dict:
        try:
            update_status(request_id, "CODE_GENERATING")
            terraform_code = await asyncio.to_thread(
                self.agent.generate_terraform, cloud_provider, services, requirements, app_name, vm_size
            )
            update_status(request_id, "PLAN_GENERATED", terraform_code=terraform_code)

            plan_output = await asyncio.to_thread(
                self.agent.run_plan, terraform_code, request_id
            )
            update_status(request_id, "COST_ESTIMATED", plan_output=plan_output)

            cost_json = await asyncio.to_thread(
                self.agent.estimate_cost, terraform_code, request_id
            )
            update_status(request_id, "WAITING_FOR_APPROVAL", cost_estimate=cost_json)
            return {"status": "WAITING_FOR_APPROVAL"}

        except Exception as e:
            update_status(request_id, "FAILED", plan_output=str(e))
            return {"status": "FAILED", "error": str(e)}

    async def deploy(self, request_id: int) -> dict:
        db = sqlite3.connect("requests.db")
        db.row_factory = sqlite3.Row
        row = db.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
        db.close()

        if not row:
            return {"error": f"Request {request_id} not found"}

        try:
            repo_url = await asyncio.to_thread(
                self.agent.push_to_github,
                row["cloud_provider"] if "cloud_provider" in row.keys() else "aws",
                row["terraform_code"],
                request_id,
                row["requirements"],
                row["app_name"] if "app_name" in row.keys() else "",
            )
            update_status(request_id, "COMPLETED", github_repo=repo_url)
            return {"repo_url": repo_url}

        except Exception as e:
            update_status(request_id, "FAILED", plan_output=str(e))
            return {"error": str(e)}
