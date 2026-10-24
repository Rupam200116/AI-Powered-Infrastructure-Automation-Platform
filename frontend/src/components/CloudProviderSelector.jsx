// CloudProviderSelector.jsx
import { useEffect, useState } from "react"
import { getProviders } from "../api"

export default function CloudProviderSelector({ cloudProvider, setCloudProvider, onNext }) {
  const [providers, setProviders] = useState(null)
  const [error, setError] = useState("")

  useEffect(() => {
    getProviders()
      .then(setProviders)
      .catch(e => setError(e.message || "Failed to load cloud providers"))
  }, [])

  if (error) return <div className="card"><p className="error-banner">⚠️ {error}</p></div>
  if (!providers) return <div className="card"><p>Loading cloud providers…</p></div>

  return (
    <div className="card">
      <h2 className="card-title">1. Select Cloud Provider</h2>
      <p className="card-subtitle">Choose which cloud you want to deploy this application to</p>

      <div className="provider-grid">
        {Object.entries(providers).map(([id, cfg]) => {
          const selected = cloudProvider === id
          return (
            <button
              key={id}
              className={`provider-card ${selected ? "selected" : ""}`}
              style={{
                borderColor: selected ? cfg.color : undefined,
                background: selected ? `${cfg.color}14` : undefined, // ~8% tint
              }}
              onClick={() => setCloudProvider(id)}
            >
              <span className="provider-dot" style={{ background: cfg.color }} />
              <span className="svc-label">{cfg.label}</span>
              <span className="svc-desc">{cfg.services.length} services available</span>
              {selected && <span className="check" style={{ color: cfg.color }}>✓</span>}
            </button>
          )
        })}
      </div>

      <button className="btn-primary" onClick={onNext} disabled={!cloudProvider}>
        Continue →
      </button>
    </div>
  )
}
