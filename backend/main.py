# backend/main.py
# FastAPI backend — handles all HTTP endpoints.
# Run with: uvicorn main:app --reload

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import json
import os
from datetime import datetime

from workflow import WorkflowEngine
from agent.providers import PROVIDERS, catalog_for_frontend, validate_provider, validate_services

app = FastAPI(title="Infra Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Database ──────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect("requests.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            cloud_provider  TEXT DEFAULT 'aws',
            app_name        TEXT,
            services        TEXT,
            requirements    TEXT,
            vm_size         TEXT DEFAULT '',
            status          TEXT DEFAULT 'PENDING',
            terraform_code  TEXT,
            plan_output     TEXT,
            cost_estimate   TEXT,
            github_repo     TEXT,
            created_at      TEXT,
            updated_at      TEXT
        )
    """)
    # migrate older DBs (pre-multicloud) that lack these columns
    existing_cols = {row["name"] for row in db.execute("PRAGMA table_info(requests)")}
    if "cloud_provider" not in existing_cols:
        db.execute("ALTER TABLE requests ADD COLUMN cloud_provider TEXT DEFAULT 'aws'")
    if "vm_size" not in existing_cols:
        db.execute("ALTER TABLE requests ADD COLUMN vm_size TEXT DEFAULT ''")
        if "instance_type" in existing_cols:
            db.execute("UPDATE requests SET vm_size = instance_type WHERE vm_size = ''")
    db.commit()
    db.close()


init_db()


# ── Request models ─────────────────────────────────────────────────────────────

class OnboardRequest(BaseModel):
    cloud_provider: str
    services:       List[str]
    requirements:   str
    app_name:       str
    vm_size:        Optional[str] = None


class ApproveRequest(BaseModel):
    request_id: int
    action:     str   # "approve" or "reject"


# ── Workflow engine ────────────────────────────────────────────────────────────

engine = WorkflowEngine()


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/api/providers")
def list_providers():
    """
    Frontend calls this first to render the cloud-provider selection page
    and then the service catalog for whichever provider is chosen.
    """
    return catalog_for_frontend()


@app.post("/api/onboard")
async def create_request(req: OnboardRequest):
    """
    User picks a cloud provider + services + requirements.
    Agent generates terraform code, validates it, estimates cost.
    """
    try:
        provider = validate_provider(req.cloud_provider)
        validate_services(provider, req.services)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    vm_size = req.vm_size or PROVIDERS[provider]["default_vm_size"]

    db = get_db()
    now = datetime.now().isoformat()

    cursor = db.execute(
        "INSERT INTO requests (cloud_provider, app_name, services, requirements, vm_size, status, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (provider, req.app_name, json.dumps(req.services), req.requirements, vm_size, "CODE_GENERATING", now, now)
    )
    request_id = cursor.lastrowid
    db.commit()
    db.close()

    result = await engine.run(request_id, provider, req.services, req.requirements, req.app_name, vm_size)

    return {
        "request_id": request_id,
        "status": result["status"],
        "message": "Agent finished processing"
    }


@app.get("/api/request/{request_id}")
def get_request(request_id: int):
    db = get_db()
    row = db.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
    db.close()

    if not row:
        raise HTTPException(status_code=404, detail="Request not found")

    return dict(row)


@app.get("/api/requests")
def list_requests():
    db = get_db()
    rows = db.execute("SELECT * FROM requests ORDER BY created_at DESC").fetchall()
    db.close()
    return [dict(r) for r in rows]


@app.post("/api/approve")
async def approve_request(req: ApproveRequest):
    """
    Approve → push code to GitHub (triggers terraform apply via Actions).
    Reject  → mark as rejected.
    """
    db = get_db()
    row = db.execute("SELECT * FROM requests WHERE id=?", (req.request_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Request not found")
    db.close()

    if req.action == "reject":
        db = get_db()
        db.execute(
            "UPDATE requests SET status='REJECTED', updated_at=? WHERE id=?",
            (datetime.now().isoformat(), req.request_id)
        )
        db.commit()
        db.close()
        return {"message": "Request rejected"}

    if req.action == "approve":
        db = get_db()
        db.execute(
            "UPDATE requests SET status='APPLYING_INFRA', updated_at=? WHERE id=?",
            (datetime.now().isoformat(), req.request_id)
        )
        db.commit()
        db.close()

        result = await engine.deploy(req.request_id)

        if "error" in result:
            raise HTTPException(status_code=500, detail=f"Deploy failed for request #{req.request_id}: {result['error']}")

        return {
            "message": "Deployment started",
            "github_repo": result.get("repo_url")
        }

    raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")


@app.get("/health")
def health_check():
    return {"status": "ok"}
