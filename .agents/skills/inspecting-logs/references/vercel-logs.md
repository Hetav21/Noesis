# Vercel Logs Reference

Detailed reference for inspecting build logs, runtime errors, and deployment health for Next.js frontend deployments on Vercel.

## Contents
- [Target Projects in this Repository](#target-projects-in-this-repository)
- [Vercel CLI Commands](#vercel-cli-commands)
- [Deployment Logs vs Runtime Logs](#deployment-logs-vs-runtime-logs)
- [Programmatic REST API](#programmatic-rest-api)
- [Authentication and Scope Flags](#authentication-and-scope-flags)
- [Common Errors & Solutions](#common-errors--solutions)

---

## Target Projects in this Repository

Configured via environment variables:
- **Web Frontend (`apps/web`):**
  - **Project Name:** `noesis`
  - **Project ID Variable:** `$VERCEL_PROJECT_ID`
  - **Production URL:** `https://noesis.hetav.dev`
- **API Project:**
  - **Project Name:** `noesis-api`
  - **Project ID Variable:** `$VERCEL_API_PROJECT_ID`
- **Team / Organization Scope:**
  - **Org ID Variable:** `$VERCEL_ORG_ID`

---

## Vercel CLI Commands

All commands support `--token "$VERCEL_TOKEN"` and `--scope "$VERCEL_ORG_ID"` for non-interactive execution.

### 1. List Deployments (`vercel ls`)
```bash
# List recent deployments for the web project
vercel ls noesis --token "$VERCEL_TOKEN" --scope "$VERCEL_ORG_ID"
```

### 2. Inspect Deployment Details (`vercel inspect`)
```bash
# Inspect a specific deployment URL or deployment ID
vercel inspect <deployment-url-or-id> --token "$VERCEL_TOKEN" --scope "$VERCEL_ORG_ID"
```
Returns:
- Build status (`● Ready`, `● Building`, `● Error`).
- Build duration and CPU usage.
- Serverless / Edge Function bundles.
- Assigned production and branch preview aliases.

### 3. Stream Runtime Logs (`vercel logs`)
```bash
# Tail live function & runtime logs
vercel logs <deployment-url> --token "$VERCEL_TOKEN" --scope "$VERCEL_ORG_ID" --follow

# Output unformatted raw logs for filtering
vercel logs <deployment-url> --token "$VERCEL_TOKEN" --scope "$VERCEL_ORG_ID" --output=raw | grep -i error
```

---

## Deployment Logs vs Runtime Logs

Vercel separates logs into two categories:

1. **Build / Deployment Logs**:
   - Output from `next build`, TypeScript compilation, and linting during deployment.
   - Best accessed via the Deployment Events REST API (see below) or by viewing the build phase in `vercel inspect`.

2. **Runtime Logs (Serverless Functions / Edge Routes)**:
   - Output from Next.js server components, API route handlers (`/api/*`), and server actions.
   - Streamed in real-time via `vercel logs <url> --follow`.

---

## Programmatic REST API

The Vercel REST API allows instant, headless log retrieval without CLI installation.

### 1. Get Latest Deployment ID for Project
```bash
curl -s -H "Authorization: Bearer $VERCEL_TOKEN" \
  "https://api.vercel.com/v6/deployments?projectId=$VERCEL_PROJECT_ID&limit=1"
```

### 2. Fetch Build and Runtime Events (Logs)
```bash
# Fetch last 30 log events for a deployment
curl -s -H "Authorization: Bearer $VERCEL_TOKEN" \
  "https://api.vercel.com/v3/deployments/<deployment-id>/events?limit=30"
```

Response structure:
```json
[
  {
    "type": "stdout",
    "text": "Running build in Washington, D.C., USA (East)...",
    "created": 1794666624036
  },
  {
    "type": "stderr",
    "text": "Failed to compile...",
    "created": 1794666625120
  }
]
```

### 3. Stream Events Live via API
```bash
# Streaming mode (follow=1 streams events as they occur)
curl -N -s -H "Authorization: Bearer $VERCEL_TOKEN" \
  "https://api.vercel.com/v3/deployments/<deployment-id>/events?follow=1"
```

---

## Authentication and Scope Flags

Because Vercel projects belong to team scopes, commands must specify `--scope`:

- Token: `--token "$VERCEL_TOKEN"`
- Scope: `--scope "$VERCEL_ORG_ID"`

Alternatively, if you run `vercel link` inside `apps/web`, Vercel creates `.vercel/project.json` which persists the project and org IDs locally.

---

## Common Errors & Solutions

| Error Message | Cause | Resolution |
|---|---|---|
| `You defined "--token", but it's missing a value` | `$VERCEL_TOKEN` was not exported in current shell | Ensure `$VERCEL_TOKEN` is exported in the shell environment |
| `Can't find the deployment "..."` | Passed a project ID instead of a deployment URL/ID to `inspect` | Pass deployment URL (e.g. `https://<deployment-url>.vercel.app`) or query deployment ID first |
| `Could not find project under scope` | Missing `--scope "$VERCEL_ORG_ID"` | Add `--scope "$VERCEL_ORG_ID"` to the command |
| Build failed with 404 or missing environment variable | Missing build-time environment variable on Vercel | Check Project Settings → Environment Variables on Vercel dashboard |
