# How to Run InfraAgent

## Prerequisites
- Python 3.11, Node.js 18+, Ollama, Terraform CLI
- GitHub token with `repo` + `workflow` scopes

---

## 1. Activate venv (run once, then every session)

```powershell
cd D:\College_Project\infra-agent
.\venv\Scripts\Activate.ps1
```

If you get "execution policy" error, run once as admin:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 2. Set PYTHONPATH

```powershell
$env:PYTHONPATH = "D:\College_Project\infra-agent"
```

---

## 3. Start Backend

```powershell
cd D:\College_Project\infra-agent\backend
uvicorn main:app --reload --port 8000
```

---

## 4. Start Frontend (new terminal)

```powershell
cd D:\College_Project\infra-agent\frontend
npm install   # first time only
npm run dev
```

Open browser at http://localhost:3000

---

## 5. Make sure Ollama is running (new terminal)

```powershell
ollama serve
# and pull the model if not already done:
ollama pull codellama:7b
```

For faster responses use a smaller model:
```powershell
ollama pull mistral:7b
```
Then update OLLAMA_MODEL in your .env file.

---

## One-liner to start everything (PowerShell)

```powershell
# Terminal 1 — backend
cd D:\College_Project\infra-agent
.\venv\Scripts\Activate.ps1
$env:PYTHONPATH = "D:\College_Project\infra-agent"
cd backend; uvicorn main:app --reload --port 8000

# Terminal 2 — frontend
cd D:\College_Project\infra-agent\frontend; npm run dev

# Terminal 3 — ollama
ollama serve
```
