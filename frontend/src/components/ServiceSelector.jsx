// ServiceSelector.jsx
import { useEffect, useState } from "react"
import { getProviders } from "../api"

export default function ServiceSelector({
  cloudProvider,
  selectedServices, setSelectedServices,
  appName, setAppName,
  requirements, setRequirements,
  vmSize, setVmSize,
  onSubmit, loading,
}) {
  const [providers, setProviders] = useState(null)
  const [error, setError] = useState("")

  useEffect(() => {
    getProviders()
      .then(data => {
        setProviders(data)
        const cfg = data[cloudProvider]
        if (cfg && !vmSize) setVmSize(cfg.default_vm_size)
      })
      .catch(e => setError(e.message || "Failed to load services"))
  }, [cloudProvider])

  const toggle = (id) =>
    setSelectedServices(prev => prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id])

  if (error) return <div className="card"><p className="error-banner">⚠️ {error}</p></div>
  if (!providers) return <div className="card"><p>Loading services…</p></div>

  const cfg = providers[cloudProvider]
  if (!cfg) return <div className="card"><p className="error-banner">⚠️ Unknown cloud provider: {cloudProvider}</p></div>

  return (
    <div className="card">
      <h2 className="card-title">2. Select {cfg.label} Services</h2>
      <p className="card-subtitle">Click the services you need for your application</p>

      <div className="services-grid">
        {cfg.services.map(svc => {
          const selected = selectedServices.includes(svc.id)
          return (
            <button
              key={svc.id}
              className={`service-card ${selected ? "selected" : ""}`}
              style={{
                borderColor: selected ? svc.color : undefined,
                background: selected ? `${svc.color}14` : undefined,
              }}
              onClick={() => toggle(svc.id)}
            >
              <span className="svc-icon" style={{ color: svc.color }}>{svc.icon}</span>
              <span className="svc-label">{svc.label}</span>
              <span className="svc-desc">{svc.desc}</span>
              {selected && <span className="check" style={{ color: svc.color }}>✓</span>}
            </button>
          )
        })}
      </div>

      {selectedServices.length > 0 && (
        <div className="selected-pill" style={{ color: cfg.color, borderColor: `${cfg.color}4d`, background: `${cfg.color}1a` }}>
          Selected: {selectedServices.join(", ")}
        </div>
      )}

      {/* VM size dropdown — only shown when this provider's VM service is selected */}
      {selectedServices.includes(cfg.vm_service) && (
        <div className="form-group">
          <label>{cfg.services.find(s => s.id === cfg.vm_service)?.label} Size</label>
          <select className="input" value={vmSize} onChange={e => setVmSize(e.target.value)}>
            {cfg.vm_sizes.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </div>
      )}

      <div className="form-group">
        <label>App Name</label>
        <input className="input" value={appName} onChange={e => setAppName(e.target.value)}
          placeholder="e.g. payment-service" />
      </div>

      <div className="form-group">
        <label>Requirements (plain English)</label>
        <textarea className="textarea" rows={4} value={requirements}
          onChange={e => setRequirements(e.target.value)}
          placeholder="e.g. Production environment, needs autoscaling, team: fintech" />
      </div>

      <button className="btn-primary" onClick={onSubmit} disabled={loading}>
        {loading ? "⏳ AI Agent Working..." : `🚀 Generate ${cfg.label} Terraform Plan`}
      </button>
    </div>
  )
}
