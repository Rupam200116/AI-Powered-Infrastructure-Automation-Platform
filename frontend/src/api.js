// api.js
const BASE = "http://localhost:8000/api"

export async function getProviders() {
  const res = await fetch(`${BASE}/providers`)
  if (!res.ok) throw new Error("Failed to fetch cloud providers")
  return res.json()
}

export async function onboard(cloudProvider, services, requirements, appName, vmSize) {
  const res = await fetch(`${BASE}/onboard`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      cloud_provider: cloudProvider,
      services,
      requirements,
      app_name: appName,
      vm_size: vmSize,
    })
  })
  if (!res.ok) {
    const text = await res.text()
    // Try to extract the "detail" field from FastAPI error JSON
    try { throw new Error(JSON.parse(text).detail) } catch { throw new Error(text) }
  }
  return res.json()
}

export async function getRequest(id) {
  const res = await fetch(`${BASE}/request/${id}`)
  if (!res.ok) throw new Error("Failed to fetch request")
  return res.json()
}

export async function approveRequest(id, action) {
  const res = await fetch(`${BASE}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ request_id: id, action })
  })
  if (!res.ok) {
    const text = await res.text()
    try { throw new Error(JSON.parse(text).detail) } catch { throw new Error(text) }
  }
  return res.json()
}
