// StatusTracker.jsx — Step 3: Shows deployment progress + repo URL + AWS secrets guide

import { useState, useEffect } from "react"
import { getRequest } from "../api"

export default function StatusTracker({ requestId }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    if (!requestId) return
    const iv = setInterval(async () => {
      try {
        const req = await getRequest(requestId)
        setData(req)
        if (req.status === "COMPLETED" || req.status === "FAILED") clearInterval(iv)
      } catch(e) { console.error(e) }
    }, 2000)
    return () => clearInterval(iv)
  }, [requestId])

  const STEPS = [
    { label: "Request Approved",          done: ["APPLYING_INFRA","COMPLETED"] },
    { label: "Code pushed to GitHub",     done: ["APPLYING_INFRA","COMPLETED"] },
    { label: "GitHub Actions triggered",  done: ["COMPLETED"] },
    { label: "AWS resources provisioned", done: ["COMPLETED"] },
  ]

  const isDone = s => data && s.done.includes(data.status)

  return (
    <div className="card">
      <h2 className="card-title">3. Deployment Progress</h2>

      {/* Status banners */}
      {data?.status === "COMPLETED" && (
        <div className="success-banner">Code pushed to GitHub. Deployment pipeline triggered automatically.</div>
      )}
      {data?.status === "FAILED" && (
        <div className="error-banner" style={{marginBottom:16}}>
          <strong>Deployment failed</strong>
          {data.plan_output && (
            <pre style={{marginTop:8,fontSize:12,whiteSpace:"pre-wrap",wordBreak:"break-word",
              background:"#0d1117",padding:10,borderRadius:6,maxHeight:180,overflowY:"auto",color:"#ff9999"}}>
              {data.plan_output}
            </pre>
          )}
        </div>
      )}
      {!data && <p className="hint">Loading status...</p>}

      {/* Progress steps */}
      <div className="deploy-steps">
        {STEPS.map((s,i) => (
          <div key={i} className={`deploy-step ${isDone(s)?"done":""}`}>
            <div className={`deploy-dot ${isDone(s)?"green":"grey"}`}>{isDone(s)?"✓":i+1}</div>
            <span>{s.label}</span>
          </div>
        ))}
      </div>

      {/* Repo link */}
      {data?.github_repo && (
        <div style={{marginTop:20}}>
          <div className="github-link">
            <span style={{color:"var(--muted)",fontSize:13}}>Repository: </span>
            <a href={data.github_repo} target="_blank" rel="noreferrer">{data.github_repo}</a>
          </div>

          <p className="hint" style={{marginTop:10}}>
            GitHub Actions will run <code>terraform apply</code> and provision your resources automatically.
          </p>
        </div>
      )}
    </div>
  )
}
