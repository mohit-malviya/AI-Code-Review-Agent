# AI Code Review Agent — Complete Flow, Setup, and Local Test

This guide explains how the agent works and how to run the same local test we used:
a laptop running the FastAPI app, ngrok exposing it, and a **separate empty GitHub repo**
that receives reviews. Do **not** push test code into the agent repository
(`mohitmalviya-skilltect/AI-Code-Review-Agent` or whatever fork you cloned).

---

## 1. How it works

```
Developer opens or updates a Pull Request
        │
        ▼
GitHub webhook  POST /webhook
        │
        ▼
ngrok (local) or Cloud Run (deployed)
        │
        ▼
FastAPI app (this repo)
        │
        ├─ Fetch PR files with GITHUB_TOKEN
        ├─ Secret scanner
        ├─ Gemini review (GEMINI_API_KEY)
        ├─ Post inline comments + summary review on the PR
        └─ Optional: generate fixes → approval email (Resend)
```

### What triggers a review

| GitHub event | What the agent does |
|---|---|
| `ping` | Accepted, then ignored (webhook connectivity check) |
| `push` | Logged only. **No AI review.** |
| `pull_request` + `opened` / `reopened` / `synchronize` | Full review |
| Other PR actions (`closed`, `edited`, …) | Skipped |

`synchronize` = new commits pushed to an **open PR** branch.

### Main URLs (local)

| URL | Purpose |
|---|---|
| `http://localhost:8000/` | Status JSON |
| `http://localhost:8000/health` | Liveness |
| `http://localhost:8000/docs` | Swagger UI |
| `POST /webhook` | GitHub webhook |
| `http://localhost:8000/approval/{id}` | Approve / reject proposed fixes |

The agent process reviews **other repos**. The empty test repo is the **subject**. This project is the **reviewer**.

---

## 2. Prerequisites

- macOS / Linux / Windows
- **Python 3.13** (recommended). Python 3.14 can fail to install `requirements.txt`
  (`packaging==26.3` vs `streamlit` needing `packaging<26`). Use `python3.13`.
- A Gemini API key ([Google AI Studio](https://aistudio.google.com/apikey))
- A GitHub account and a repo **you admin** (to add a webhook)
- A fine-grained GitHub PAT with access to **that** repo
- ngrok (only for local GitHub → laptop)

---

## 3. Install the agent (this repo)

```bash
cd /path/to/AI-Code-Review-Agent

# Prefer 3.13. Example: python3.13
python3.13 -m venv venv
source venv/bin/activate          # Windows: .\venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -r requirements.txt
```

If install fails on `packaging==26.3` vs Streamlit, pin:

```text
packaging==25.0
```

then run `pip install -r requirements.txt` again.

`python3` alone may be 3.14 — check with `python --version` after activating the venv.

---

## 4. Environment file

Create `.env` in the **agent** project root (same folder as `requirements.txt`).
Do not commit it (`.gitignore` already lists `.env`).

```bash
# Required — app will not start without this
GEMINI_API_KEY=your_gemini_api_key

# Required to read PR files and post comments (YOUR token, YOUR test repo)
GITHUB_TOKEN=github_pat_your_token

# Optional for first test (GitHub comments still work without email)
RESEND_API_KEY=re_your_key
APPROVAL_FROM_EMAIL=onboarding@resend.dev
APPROVAL_RECIPIENT_EMAIL=you@example.com
APPROVAL_BASE_URL=http://localhost:8000/approval

# Leave empty locally if the GitHub webhook Secret is also empty
GITHUB_WEBHOOK_SECRET=

# Leave empty locally (JSON file). Use firestore on Cloud Run.
STORAGE_BACKEND=
```

### What to use vs a teammate’s shared values

| Variable | Shared teammate value? |
|---|---|
| `GEMINI_API_KEY` | OK for a quick demo if still valid; prefer your own |
| `GITHUB_TOKEN` | **Replace. Must be yours** and scoped to the repo you review |
| `RESEND_API_KEY` | Teammate sandbox can only email **their** verified address |
| `APPROVAL_RECIPIENT_EMAIL` | Set to **your** email if you want the approve link |
| `APPROVAL_FROM_EMAIL` | Keep `onboarding@resend.dev` for Resend test mode |
| `APPROVAL_BASE_URL` | `http://localhost:8000/approval` locally |

`GITHUB_TOKEN` is loaded at import time. **Restart uvicorn** after you change `.env`.
`--reload` does not reliably pick up `.env` changes.

### Fine-grained PAT (GitHub)

1. GitHub → **Settings → Developer settings → Personal access tokens → Fine-grained tokens**
2. **Only select repositories** → pick the repo that will receive reviews
3. **+ Add permissions** (Repositories tab, not Account):
   - **Contents** → Read and write
   - **Pull requests** → Read and write
   - **Metadata** → Read
4. Generate and put the value in `GITHUB_TOKEN`

---

## 5. Start the agent

```bash
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Check:

- http://localhost:8000 → `status: online`
- http://localhost:8000/docs
- http://localhost:8000/health

Optional: preview the approval UI without GitHub:

```bash
python create_demo_ui.py
```

Open the printed `http://localhost:8000/approval/<id>` URL.

---

## 6. Expose localhost with ngrok

GitHub cannot call `localhost`. Keep uvicorn running. In a **second** terminal:

```bash
brew install ngrok
ngrok config add-authtoken YOUR_NGROK_AUTHTOKEN
ngrok http 8000
```

Copy **Forwarding**, for example:

```text
https://your-subdomain.ngrok-free.dev
```

Do **not** use ngrok’s dashboard example `ngrok http 80` or a random demo host.
This app is on **port 8000**.

Webhook URL:

```text
https://<your-ngrok-host>/webhook
```

Free ngrok URLs can change when you restart ngrok. Update the GitHub webhook if the host changes.

---

## 7. Create a test repo (do not use the agent repo)

You need **admin** on the repo to add a webhook. You cannot add a webhook on a
teammate’s repo unless they grant Admin or add the webhook for you.

Example used in our test: `Kishor-SkillTect/ai-review-test` (empty).

### Add the webhook (on YOUR repo)

**Settings → Webhooks → Add webhook**

| Field | Value |
|---|---|
| Payload URL | `https://<your-ngrok-host>/webhook` |
| Content type | `application/json` |
| Secret | leave **blank** (do not type the word empty) |
| Events | **Let me select individual events** → **Pull requests** only |
| Active | checked |

Save. Uvicorn should show:

```text
GitHub Event Received: ping
IGNORING EVENT: ping
POST /webhook  200 OK
```

That only proves connectivity. A **Pull Request** starts the review.

---

## 8. End-to-end test script (separate folder)

Run this in a **new** terminal. **Do not** `cd` into `AI-Code-Review-Agent`.
Replace the remote if your test repo name/user is different.

```bash
mkdir -p ~/AgenticAi/ai-review-test
cd ~/AgenticAi/ai-review-test

git init
git branch -M main
git remote add origin https://github.com/YOUR_GITHUB_USER/YOUR_TEST_REPO.git

printf '%s\n' '# ai-review-test' 'Test repo for the AI Code Review Agent.' > README.md
git add README.md
git commit -m "chore: add README"
git push -u origin main

git checkout -b test-ai-review

cat > app.py << 'EOF'
def login(user, password):
    query = f"SELECT * FROM users WHERE name = '{user}' AND password = '{password}'"
    return db.execute(query)

SECRET = "sk_live_dummy_key_12345"

def average(nums):
    return sum(nums) / len(nums)
EOF

git add app.py
git commit -m "test: add sample code for AI review"
git push -u origin test-ai-review
```

Before `git push`, confirm remote is **your** test repo, not the agent repo:

```bash
git remote -v
```

Must **not** contain `mohitmalviya-skilltect/AI-Code-Review-Agent`.

Open the PR:

```text
https://github.com/YOUR_GITHUB_USER/YOUR_TEST_REPO/compare/main...test-ai-review
```

Click **Create pull request**.

Or:

```bash
gh pr create --title "Test AI review" --body "Trigger local AI Code Review Agent"
```

### Manual alternative (GitHub UI, empty repo)

1. On the empty repo page click **creating a new file**
2. Name `README.md`, commit to `main`
3. **Add file → Create new file** → `app.py` with the sample above
4. Choose **Create a new branch … and start a pull request**
5. Branch `test-ai-review` → **Create pull request**

---

## 9. What success looks like

**Uvicorn**

```text
GitHub Event Received: pull_request
PROCESSING PULL REQUEST EVENT
Pull Request Action: opened
Repository: YOUR_USER/YOUR_TEST_REPO
PR Number: 1
File: app.py
SENDING ALL FILES TO GEMINI
POSTING PR INLINE COMMENTS
Status: 201
PR REVIEW POSTED TO GITHUB
```

**GitHub PR**

- Inline comment on `average()` (empty list / ZeroDivisionError)
- Conversation tab: **AI Code Review** summary

Sample issues you should see: SQL injection in `login`, hardcoded `SECRET`, divide-by-zero in `average`.

### Re-trigger on the same PR

```bash
cd ~/AgenticAi/ai-review-test
echo "" >> app.py
git add app.py
git commit -m "test: retrigger review"
git push
```

That sends `synchronize`.

---

## 10. Problems we actually hit

| Symptom | Cause | Fix |
|---|---|---|
| `pip: command not found` | venv not activated | `source venv/bin/activate` |
| `ResolutionImpossible` on `packaging` | `packaging==26.3` vs Streamlit `<26` | Pin `packaging==25.0`; use Python 3.13 |
| `GET /json/version` 404 | Browser / DevTools probe | Ignore |
| Settings: “You don’t have access” | Not admin on teammate’s repo | Use your own repo or ask for Admin |
| `ping` only, no review | Push to `main` with no PR | Open a Pull Request |
| Review in logs, **403** on comments | Uvicorn still had old/teammate token | Restart uvicorn after `.env` change |
| Token UI only shows Account permissions | **Public repositories** selected | **Only select repositories** → **+ Add permissions** |
| Approval email failed | Resend test mode only emails the key owner | Own Resend domain, or recipient = key owner |
| ngrok URL dead | Restarted ngrok, host changed | Update webhook Payload URL |

---

## 11. Keep these running while testing

1. Terminal A: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
2. Terminal B: `ngrok http 8000`
3. Do not push test files into the agent git remote

---

## 12. Tests (optional)

```bash
source venv/bin/activate
pytest
```

---

## 13. Docker (optional)

```bash
docker build -t ai-code-review-agent .
docker run -p 8080:8080 --env-file .env ai-code-review-agent
```

Docker listens on **8080**, not 8000.
