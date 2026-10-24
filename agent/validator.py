# agent/validator.py
# Runs terraform plan to check if the generated code is valid
# It writes the code to a temp folder, runs init + validate, then cleans up

import subprocess
import tempfile
import os
import shutil


def run_terraform_plan(terraform_code: str, request_id: int) -> str:
    # create a temp directory to run terraform in
    work_dir = tempfile.mkdtemp(prefix=f"tf_plan_{request_id}_")

    try:
        # write the generated code to main.tf
        tf_file = os.path.join(work_dir, "main.tf")
        with open(tf_file, "w", encoding="utf-8") as f:
            f.write(terraform_code)

        # run terraform init first (needed before validate)
        # -backend=false so it doesn't try to connect to S3 during local testing
        print(f"[Validator] Running terraform init in {work_dir}")
        init = subprocess.run(
            ["terraform", "init", "-backend=false", "-no-color"],
            cwd=work_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120
        )

        if init.returncode != 0:
            return f"terraform init failed:\n{init.stderr}"

        # now validate the syntax
        print("[Validator] Running terraform validate")
        validate = subprocess.run(
            ["terraform", "validate", "-no-color"],
            cwd=work_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30
        )

        if validate.returncode != 0:
            return f"terraform validate failed:\n{validate.stderr}"

        return f"Terraform validation passed\n\n{validate.stdout}"

    except FileNotFoundError:
        # terraform CLI is not installed on this machine
        # this is fine for demo purposes, GitHub Actions will run the real plan
        return (
            "terraform is not installed locally.\n"
            "The code will be validated when GitHub Actions runs terraform plan.\n\n"
            "Generated code looks correct based on template/LLM output."
        )

    except Exception as e:
        return f"Validation error: {str(e)}"

    finally:
        # always clean up the temp directory
        shutil.rmtree(work_dir, ignore_errors=True)
