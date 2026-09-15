# How to Integrate the AI Code Review Agent

This document is for connecting the agent to a **real** repository (yours or a team’s).
For a first local walkthrough, see [COMPLETE_FLOW.md](./COMPLETE_FLOW.md).

There are two roles:

| Role | Responsibility |
|---|---|
| **Agent host** | Runs this FastAPI app (laptop + ngrok, or Cloud Run) |
| **Target repo** | Repo whose PRs get reviewed. Needs a webhook + a token that can comment |

One agent process can review any repo whose webhook points at it, as long as
`GITHUB_TOKEN` can access that repo.

---

## 1. What you integrate (no app code changes)

You do **not** copy this agent into every product repo.
You add a **GitHub webhook** on the target repo and point it at the running agent.

```
Target repo PR  →  webhook POST /webhook  →  Agent  →  GitHub review comments
```

---

## 2. Choose where the agent runs

### A. Local (development)

- Run: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Tunnel: `ngrok http 8000`
- Webhook URL: `https://<ngrok-host>/webhook`
- Update the webhook whenever the ngrok host changes

### B. Cloud Run (shared / always on)

```bash
export GCP_PROJECT_ID='your-gcp-project-id'
./deploy_cloud_run.sh
```

Then set secrets on the service (`GEMINI_API_KEY`, `GITHUB_TOKEN`, `RESEND_API_KEY`,
`GITHUB_WEBHOOK_SECRET`, `APPROVAL_RECIPIENT_EMAIL`, `APPROVAL_FROM_EMAIL`) and:

```text
APPROVAL_BASE_URL=https://<cloud-run-url>/approval
STORAGE_BACKEND=firestore
```

Webhook URL:

```text
https://<cloud-run-url>/webhook
```

Use `--no-cpu-throttling` (already in `deploy_cloud_run.sh`) so background review
continues after the HTTP 202/200 response.

---

## 3. Target repo checklist

On **each** repo you want reviewed:

1. You (or a repo admin) add a webhook:
   - Payload URL: `https://<agent-host>/webhook`
   - Content type: `application/json`
   - Secret: same as `GITHUB_WEBHOOK_SECRET` (recommended in production)
   - Events: **Pull requests**
2. `GITHUB_TOKEN` on the agent host can access that repo:
   - Contents: Read and write
   - Pull requests: Read and write
   - Metadata: Read
3. Developers open **Pull Requests**. Pushing only to `main` does not review.

If you cannot open **Settings → Webhooks**, you are not an admin. Ask an admin
to add the webhook or grant Admin.

A PR from a **fork into** repo A delivers the webhook to **repo A** (the base).
The webhook must be on the repo where the PR is opened.

---

## 4. Environment variables (agent host)

| Variable | Required | Used for |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Start the process + run reviews |
| `GITHUB_TOKEN` | Yes | Read diffs, post comments / reviews, apply approved fixes |
| `GITHUB_WEBHOOK_SECRET` | Production yes | HMAC of `X-Hub-Signature-256`. If unset, signatures are allowed (dev only) |
| `RESEND_API_KEY` | For email approval | Send approve/reject email |
| `APPROVAL_FROM_EMAIL` | Email | From address. Resend test: `onboarding@resend.dev` |
| `APPROVAL_RECIPIENT_EMAIL` | Email | Who gets the approval link |
| `APPROVAL_BASE_URL` | Email | Prefix for `/approval/{id}` links |
| `STORAGE_BACKEND` | Cloud | `firestore` in production; omit locally (JSON file) |

Restart the process after changing `.env`.

---

## 5. Webhook contract

- Method: `POST /webhook`
- Header: `X-GitHub-Event` (`pull_request`, `ping`, `push`, …)
- Header: `X-Hub-Signature-256` when a secret is configured
- Body: GitHub JSON payload

The handler returns quickly and processes the review in a background task.

Handled PR actions: `opened`, `reopened`, `synchronize`.

---

## 6. What reviewers see

On the PR:

- Inline comments on changed lines
- A summary review comment (**AI Code Review**)
- Optional approval email with a link to proposed patches
- Approve on `/approval/{id}` applies commits via the GitHub API (token needs Contents write)

Loop guard: commits whose message contains `🤖 Apply AI-approved fix` are not reviewed again.

---

## 7. Integrate a second / existing product repo

1. Agent already running (local+ngrok or Cloud Run).
2. Create a PAT (or extend the existing one) to include the new repo.
3. Update `GITHUB_TOKEN` and restart the agent.
4. On the product repo: add the same webhook URL, content type `application/json`,
   event **Pull requests**.
5. Open a small PR. Confirm uvicorn/Cloud Run logs and a comment on the PR.

No clone of the agent into the product repo is required.

---

## 8. Production recommendations

- Set `GITHUB_WEBHOOK_SECRET` on both GitHub and the agent
- Do not use teammate PATs; use a bot/machine user or a dedicated fine-grained token
- Use your own Gemini and Resend accounts
- Verify a Resend domain if you email anyone other than the Resend account owner
- Prefer Cloud Run (or similar) over ngrok for a shared team webhook
- Restrict the PAT to only the repos that should be reviewed

---

## 9. Quick verify

```bash
curl -s https://<agent-host>/health
# {"status":"healthy","service":"ai-code-review-agent"}
```

GitHub → webhook → **Recent Deliveries**: `ping` and `pull_request` should be **200**.
