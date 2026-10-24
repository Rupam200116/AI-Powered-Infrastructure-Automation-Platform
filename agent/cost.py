# agent/cost.py
# Uses infracost CLI to estimate the monthly AWS cost of the generated terraform code
# If infracost is not installed it just returns a rough estimate

import subprocess
import tempfile
import os
import shutil
import json


def run_infracost(terraform_code: str, request_id: int) -> str:
    work_dir = tempfile.mkdtemp(prefix=f"tf_cost_{request_id}_")

    try:
        # write terraform code to the temp folder
        with open(os.path.join(work_dir, "main.tf"), "w", encoding="utf-8") as f:
            f.write(terraform_code)

        print(f"[Cost] Running infracost breakdown for request #{request_id}")

        result = subprocess.run(
            ["infracost", "breakdown", "--path", work_dir, "--format", "json", "--no-cache"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120
        )

        # infracost worked, return the full JSON
        if result.returncode == 0 and result.stdout:
            return result.stdout

        # sometimes infracost prints warnings but still returns valid JSON
        if result.stdout:
            return result.stdout

        # fallback if infracost gave nothing useful
        return _fallback_estimate(request_id)

    except FileNotFoundError:
        # infracost is not installed - return a placeholder
        print("[Cost] infracost not found, returning placeholder estimate")
        return _fallback_estimate(request_id)

    except Exception as e:
        print(f"[Cost] Error running infracost: {e}")
        return json.dumps({"error": str(e), "totalMonthlyCost": "unknown"})

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def _fallback_estimate(request_id: int) -> str:
    # rough estimate when infracost is not available
    return json.dumps({
        "totalMonthlyCost": "~5.00",
        "currency": "USD",
        "note": "Install infracost for exact estimates: https://www.infracost.io/docs/"
    })


def parse_cost_summary(cost_json: str) -> dict:
    # helper to pull just the total cost out of the full infracost JSON
    try:
        data = json.loads(cost_json)
        return {
            "monthly_cost": data.get("totalMonthlyCost", "N/A"),
            "currency": data.get("currency", "USD"),
        }
    except Exception:
        return {"monthly_cost": "~$5/month", "currency": "USD"}
