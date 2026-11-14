# Render Logs Reference

Detailed reference for inspecting logs, deployment events, and diagnostics for services running on Render.

## Contents
- [Target Services in this Repository](#target-services-in-this-repository)
- [Render CLI Command Options](#render-cli-command-options)
- [Log Levels and Filtering](#log-levels-and-filtering)
- [Programmatic REST API](#programmatic-rest-api)
- [SSH Access for Container Diagnostics](#ssh-access-for-container-diagnostics)
- [Common Errors & Solutions](#common-errors--solutions)

---

## Target Services in this Repository

Defined in `apps/agent/render.yaml`:
- **Service Name:** `noesis-agent`
- **Service ID Variable:** `$RENDER_SERVICE_ID`
- **Runtime:** Docker (`apps/agent/Dockerfile`)
- **Workspace Variable:** `$RENDER_WORKSPACE_ID`

---

## Render CLI Command Options

The CLI command is `render logs`. The `--resources` flag is mandatory.

```bash
render logs --resources <service-id> [flags]
```

### Supported Flags
- `--resources <id>`: Target service ID (e.g. `$RENDER_SERVICE_ID`). Comma-separated for multiple services.
- `--tail`: Stream live logs in real-time until cancelled (SIGINT / Ctrl+C).
- `--limit <n>`: Limit number of log entries returned (default: 100).
- `--level <level>`: Filter entries by log severity (`debug`, `info`, `warn`, `error`).
- `--text <query>`: Case-insensitive substring match against log lines.
- `--start <ISO8601>`: Beginning timestamp (e.g. `2026-11-14T00:00:00Z`).
- `--end <ISO8601>`: End timestamp.
- `--output <format>`: Format output (`text` or `json`). Use `json` for machine parsing in scripts.

### Examples

```bash
# Stream error logs live
render logs --resources "$RENDER_SERVICE_ID" --level error --tail

# Find database connection logs from the last hour
render logs --resources "$RENDER_SERVICE_ID" --text "database" --limit 50

# Output JSON for agent analysis
render logs --resources "$RENDER_SERVICE_ID" --output json --limit 20 | jq '.[] | {timestamp, message, level}'
```

---

## Log Levels and Filtering

The Python agent in `apps/agent` outputs standard Uvicorn and custom worker logs:
- `INFO`: Normal request lifecycle, worker job claims (`[Agent Worker] Atomically claimed queued job...`).
- `WARNING`: Slow queries, retry warnings, deprecated calls.
- `ERROR`: Unhandled exceptions, failed OpenAI/database calls, traceback dumps.

To isolate critical backend issues without noise:
```bash
render logs --resources "$RENDER_SERVICE_ID" --level error
```

---

## Programmatic REST API

If `render` CLI is not available, the Render Public API can be queried directly:

```bash
curl -s -H "Authorization: Bearer $RENDER_API_KEY" \
  "https://api.render.com/v1/services/$RENDER_SERVICE_ID/logs?limit=50"
```

Response JSON format:
```json
[
  {
    "id": "log-entry-id",
    "timestamp": "2026-11-14T12:25:31Z",
    "message": "[Agent Worker] Atomically claimed queued job...",
    "level": "info"
  }
]
```

---

## SSH Access for Container Diagnostics

Render allows opening an interactive shell directly in the running Docker container:

```bash
render ssh "$RENDER_SERVICE_ID"
```

Useful for:
- Checking disk space (`df -h`).
- Inspecting environment variables inside the live container (`env`).
- Checking running processes (`ps aux`).

---

## Common Errors & Solutions

| Error Message | Cause | Resolution |
|---|---|---|
| `run 'render login' to authenticate` | `$RENDER_API_KEY` is not exported in current shell | Ensure `$RENDER_API_KEY` is exported in the shell environment |
| `no workspace set. Use 'render workspace set'` | CLI has no active default workspace | Run `render workspace set "$RENDER_WORKSPACE_ID"` |
| `required flag(s) "resources" not set` | Omitted `--resources` argument | Always pass `--resources "$RENDER_SERVICE_ID"` |
| Service suspended / sleeping | Render free tier puts web services to sleep after inactivity | Send an HTTP request to wake up the service, then check logs |
