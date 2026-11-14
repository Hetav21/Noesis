---
name: inspecting-logs
description: Inspects, streams, tails, and filters build and runtime logs for both the Render backend agent (noesis-agent) and Vercel frontend deployments (noesis / noesis-api). Use when asked to check logs, stream logs, tail errors, inspect deployment failures, debug 500s or timeouts, or monitor services on Render or Vercel.
---

# Inspecting Logs

Guidance for inspecting build and runtime logs across deployed services: the Python backend agent on **Render** and the Next.js frontend on **Vercel**.

## Prerequisites

Expects the following environment variables to be set in your shell environment:

| Service | Host | Target ID Variable | Auth Variable(s) | CLI Binary |
|---|---|---|---|---|
| **Agent Backend** (`apps/agent`) | Render | `$RENDER_SERVICE_ID` | `$RENDER_API_KEY`, `$RENDER_WORKSPACE_ID` | `render` |
| **Web Frontend** (`apps/web`) | Vercel | `$VERCEL_PROJECT_ID` | `$VERCEL_TOKEN`, `$VERCEL_ORG_ID` | `vercel` / `vc` |

---

## 1. Render Logs (Backend Agent)

Use the official `render logs` command. The `--resources` flag is required.

```bash
# View the last 50 log lines
render logs --resources "$RENDER_SERVICE_ID" --limit 50

# Live stream / tail logs
render logs --resources "$RENDER_SERVICE_ID" --tail

# Filter by severity level (error, warn, info)
render logs --resources "$RENDER_SERVICE_ID" --level error

# Search for specific text/exceptions
render logs --resources "$RENDER_SERVICE_ID" --text "exception"

# Structured JSON output for programmatic analysis
render logs --resources "$RENDER_SERVICE_ID" --output json --limit 20
```

For advanced Render CLI options, REST API fallback, and container SSH access, see [references/render-logs.md](references/render-logs.md).

---

## 2. Vercel Logs (Frontend Web)

Use the official `vercel` CLI. Pass `--token "$VERCEL_TOKEN"` and `--scope "$VERCEL_ORG_ID"` for non-interactive authentication.

```bash
# List recent deployments to find deployment URLs
vercel ls noesis --token "$VERCEL_TOKEN" --scope "$VERCEL_ORG_ID"

# Inspect deployment build status, duration, and function routes
vercel inspect <deployment-url-or-id> --token "$VERCEL_TOKEN" --scope "$VERCEL_ORG_ID"

# Live stream runtime logs
vercel logs <deployment-url> --token "$VERCEL_TOKEN" --scope "$VERCEL_ORG_ID" --follow

# Fetch latest deployment build/runtime events via REST API
DEPLOY_ID=$(curl -s -H "Authorization: Bearer $VERCEL_TOKEN" \
  "https://api.vercel.com/v6/deployments?projectId=$VERCEL_PROJECT_ID&limit=1" \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['deployments'][0]['uid'])")

curl -s -H "Authorization: Bearer $VERCEL_TOKEN" \
  "https://api.vercel.com/v3/deployments/$DEPLOY_ID/events?limit=30"
```

For advanced Vercel CLI options and REST API details, see [references/vercel-logs.md](references/vercel-logs.md).

---

## Common CLI Issues

### "No workspace set" (Render)
If Render CLI asks to select a workspace, set it using the workspace variable:
```bash
render workspace set "$RENDER_WORKSPACE_ID"
```

### "Missing token" or "Authentication required"
Verify that `$RENDER_API_KEY` and `$VERCEL_TOKEN` are exported in the active shell.
