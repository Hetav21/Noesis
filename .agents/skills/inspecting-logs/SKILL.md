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

Use the official `render logs` command with the `--resources` flag.

```bash
# View recent logs (default: latest 100)
render logs --resources "$RENDER_SERVICE_ID" --limit 50

# Live stream / tail new logs
render logs --resources "$RENDER_SERVICE_ID" --tail

# Filter by log level (error, warn, info)
render logs --resources "$RENDER_SERVICE_ID" --level error

# Search for specific text / exceptions
render logs --resources "$RENDER_SERVICE_ID" --text "exception"

# JSON output for structured programmatic analysis
render logs --resources "$RENDER_SERVICE_ID" --output json --limit 20
```

> **Discoverability**: To see all supported filtering flags (`--start`, `--end`, `--status-code`, etc.), run:
> ```bash
> render logs --help
> ```
> If the CLI behavior differs or you need to inspect new Render CLI features, search the web or check `render --help`.

---

## 2. Vercel Logs (Frontend Web)

Use the official `vercel` CLI. Pass `--token "$VERCEL_TOKEN"` and `--scope "$VERCEL_ORG_ID"` for non-interactive execution.

```bash
# List recent deployments to find deployment URLs / IDs
vercel ls --token "$VERCEL_TOKEN" --scope "$VERCEL_ORG_ID"

# View recent runtime logs for the project
vercel logs --project "$VERCEL_PROJECT_ID" --token "$VERCEL_TOKEN" --scope "$VERCEL_ORG_ID"

# Find runtime errors across environments
vercel logs --project "$VERCEL_PROJECT_ID" --query 'level:error' --token "$VERCEL_TOKEN" --scope "$VERCEL_ORG_ID"

# Target a specific deployment
vercel logs --deployment <deployment-url-or-id> --token "$VERCEL_TOKEN" --scope "$VERCEL_ORG_ID"

# Inspect CDN requests with HTTP status >= 500
vercel logs requests --project "$VERCEL_PROJECT_ID" --query 'httpStatus >= 500' --token "$VERCEL_TOKEN" --scope "$VERCEL_ORG_ID"

# Inspect deployment build status, duration, and function routes
vercel inspect <deployment-url-or-id> --token "$VERCEL_TOKEN" --scope "$VERCEL_ORG_ID"
```

> **Discoverability**: To see all query expressions, data sources (`runtime`, `requests`), and time window flags (`--since`, `--until`), run:
> ```bash
> vercel logs --help
> vercel logs runtime --help
> vercel logs requests --help
> ```
> If you need newer CLI features or query syntax updates, run `--help` or search the web directly rather than relying on cached assumptions.

---

## Common CLI Issues

### "No workspace set" (Render)
If Render CLI prompts to select a workspace, set it using the workspace variable:
```bash
render workspace set "$RENDER_WORKSPACE_ID"
```

### "Missing token" or "Authentication required"
Verify that `$RENDER_API_KEY` and `$VERCEL_TOKEN` are exported in the active shell environment.
