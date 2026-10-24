// PlanReview.jsx — Step 2: Show generated Terraform code + cost estimate

import { useState, useEffect } from "react"
import { getRequest } from "../api"

export default function PlanReview({ requestId, onApprove, onReject, loading }) {
  const [data, setData] = useState(null)
  const [polling, setPolling] = useState(true)

  useEffect(() => {
    if (!requestId || !polling) return
    const interval = setInterval(async () => {
      try {
        const req = await getRequest(requestId)
        setData(req)
        if (req.status === "WAITING_FOR_APPROVAL" || req.status === "FAILED") {
          setPolling(false)
        }
      } catch (e) {
        console.error(e)
      }
    }, 2000)
    return () => clearInterval(interval)
  }, [requestId, polling])

  const getCostSummary = () => {
    try {
      const cost = JSON.parse(data.cost_estimate)
      return cost.totalMonthlyCost ? `$${cost.totalMonthlyCost}/month` : "Calculating..."
    } catch {
      return data?.cost_estimate ? "~$5/month" : "Calculating..."
    }
  }

  if (!data || data.status !== "WAITING_FOR_APPROVAL") {
    return (
      <div className="card">
        <h2 className="card-title">AI Agent is Working...</h2>
        <div className="pipeline-status">
          <Step label="Generating Terraform Code" done={!!data?.terraform_code} />
          <Step label="Running terraform plan" done={!!data?.plan_output} />
          <Step label="Estimating cost with Infracost" done={!!data?.cost_estimate} />
          <Step label="Waiting for your approval" done={false} active />
        </div>
        <p className="hint">This takes ~30 seconds. The AI is generating your infrastructure code.</p>
      </div>
    )
  }

  return (
    <div className="card">
      <h2 className="card-title">2. Review Your Infrastructure Plan</h2>

      <div className="cost-banner">
        <span className="cost-label">Estimated Monthly Cost:</span>
        <span className="cost-value">{getCostSummary()}</span>
      </div>

      <div className="tabs">
        <div className="tab-section">
          <h3>Generated Terraform Code</h3>
          <pre className="code-block">{data.terraform_code || "Loading..."}</pre>
        </div>

        <div className="tab-section">
          <h3>Validation Output</h3>
          <pre className="code-block plan">{data.plan_output || "Loading..."}</pre>
        </div>
      </div>

      <div className="approve-row">
        <button className="btn-danger" onClick={onReject} disabled={loading}>
          Reject
        </button>
        <button className="btn-success" onClick={onApprove} disabled={loading}>
          {loading ? "Deploying..." : "Approve & Deploy"}
        </button>
      </div>
    </div>
  )
}

function Step({ label, done, active }) {
  return (
    <div className={`pipeline-step ${done ? "done" : ""} ${active ? "active" : ""}`}>
      <span className="step-dot">{done ? "✓" : active ? "●" : "○"}</span>
      <span>{label}</span>
    </div>
  )
}
