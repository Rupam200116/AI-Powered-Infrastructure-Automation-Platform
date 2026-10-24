// App.jsx
import { useState } from "react"
import CloudProviderSelector from "./components/CloudProviderSelector"
import ServiceSelector from "./components/ServiceSelector"
import PlanReview from "./components/PlanReview"
import StatusTracker from "./components/StatusTracker"
import { onboard, approveRequest } from "./api"
import "./App.css"

const STEPS = ["Select Cloud", "Select & Describe", "Review Plan", "Deploy Status"]

export default function App() {
  const [step, setStep]                         = useState(0)
  const [cloudProvider, setCloudProvider]       = useState("")
  const [selectedServices, setSelectedServices] = useState([])
  const [appName, setAppName]                   = useState("")
  const [requirements, setRequirements]         = useState("")
  const [vmSize, setVmSize]                     = useState("")
  const [requestId, setRequestId]               = useState(null)
  const [loading, setLoading]                   = useState(false)
  const [error, setError]                       = useState("")

  // whenever the cloud provider changes, the previously selected services
  // (which belong to the old provider's catalog) are no longer valid
  const handleProviderChange = (id) => {
    setCloudProvider(id)
    setSelectedServices([])
    setVmSize("")
  }

  const handleSubmit = async () => {
    if (!selectedServices.length) return setError("Select at least one service")
    if (!appName.trim())          return setError("Enter an app name")
    if (!requirements.trim())     return setError("Describe your requirements")
    setLoading(true); setError("")
    try {
      const result = await onboard(cloudProvider, selectedServices, requirements, appName, vmSize)
      setRequestId(result.request_id)
      setStep(2)
    } catch (e) { setError(e.message || "Failed to process request") }
    finally { setLoading(false) }
  }

  const handleApprove = async (action) => {
    setLoading(true); setError("")
    try {
      await approveRequest(requestId, action)
      setStep(3)
    } catch (e) { setError(e.message || "Action failed") }
    finally { setLoading(false) }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-inner">
          <p className="header-subtitle">AI-Powered Cloud Infrastructure & DevOps Automation Platform</p>
        </div>
      </header>

      <div className="steps-bar">
        {STEPS.map((s, i) => (
          <div key={i} className={`step ${i===step?"active":""} ${i<step?"done":""}`}>
            <span className="step-num">{i < step ? "✓" : i + 1}</span>
            <span className="step-label">{s}</span>
          </div>
        ))}
      </div>

      <main className="main-content">
        {error && <div className="error-banner">⚠️ {error}</div>}

        {step === 0 && (
          <CloudProviderSelector
            cloudProvider={cloudProvider} setCloudProvider={handleProviderChange}
            onNext={() => setStep(1)}
          />
        )}
        {step === 1 && (
          <ServiceSelector
            cloudProvider={cloudProvider}
            selectedServices={selectedServices} setSelectedServices={setSelectedServices}
            appName={appName} setAppName={setAppName}
            requirements={requirements} setRequirements={setRequirements}
            vmSize={vmSize} setVmSize={setVmSize}
            onSubmit={handleSubmit} loading={loading}
          />
        )}
        {step === 2 && (
          <PlanReview
            requestId={requestId}
            onApprove={() => handleApprove("approve")}
            onReject={() => handleApprove("reject")}
            loading={loading}
          />
        )}
        {step === 3 && <StatusTracker requestId={requestId} />}
      </main>
    </div>
  )
}
