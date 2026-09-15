# AI-Code-Review-Agent

AI agent that reviews GitHub pull requests (Gemini), posts comments, and can propose fixes for approval.

## Docs

| Guide | Use it when |
|---|---|
| [docs/COMPLETE_FLOW.md](docs/COMPLETE_FLOW.md) | How it works, local install, ngrok, env vars, and the full test script |
| [docs/INTEGRATION.md](docs/INTEGRATION.md) | Hook the agent up to another repo (webhook, token, Cloud Run) |

## Quick start

```bash
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# create .env (see COMPLETE_FLOW.md)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Reviews run on **Pull Request** events (`opened`, `reopened`, `synchronize`), not on a plain `git push`.
