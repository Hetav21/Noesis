---
name: accessing-database
description: Connects to, inspects, queries, and troubleshoots PostgreSQL databases (including Neon serverless postgres). Use when asked to check database health, discover schemas, inspect tables, run ad-hoc queries, check migrations, or troubleshoot database connectivity and connection pool issues.
---

# Accessing the Database

Guidance for connecting to, inspecting, and querying PostgreSQL databases (including serverless PostgreSQL on **Neon**).

## Prerequisites

The database connection string is expected in the active environment via `DATABASE_URL`.

| Variable | Description |
|---|---|
| `$DATABASE_URL` | Active PostgreSQL connection string (`postgresql://...` or `postgresql+asyncpg://...`) |
| `$ALLOW_UNBOUND_CHANNEL` | Permits stripping unsupported channel binding parameters if present |

> **Security Guardrail**: Never hardcode database connection strings, passwords, or endpoints into files, scripts, or commit history. Always read `$DATABASE_URL` dynamically from the environment.

---

## 1. Direct CLI Access with `psql`

`psql` is available in the shell environment (via `flake.nix`).

### Connection String Normalization

PostgreSQL CLI tools require the standard `postgresql://` scheme. If `$DATABASE_URL` includes an ORM/driver prefix (such as `postgresql+asyncpg://`), normalize it before invoking `psql`:

```bash
# Normalize connection URL for standard PostgreSQL clients
PG_URL="${DATABASE_URL/postgresql+asyncpg:\/\//postgresql:\/\/}"
```

### Dynamic Schema Discovery

Always discover tables and column structures dynamically rather than assuming a static schema:

```bash
# 1. Test connectivity
psql "$PG_URL" -c "SELECT 1;"

# 2. List all user tables in the database
psql "$PG_URL" -c "\dt"

# 3. Inspect columns, constraints, and indexes for any specific table
psql "$PG_URL" -c "\d+ <table_name>"

# 4. View table sizes and estimated live row counts
psql "$PG_URL" -c "
  SELECT relname AS table_name, n_live_tup AS row_estimate 
  FROM pg_stat_user_tables 
  ORDER BY n_live_tup DESC;
"
```

### Safe Non-Interactive Querying

When executing queries in automated agent shells:
- Pass `-P pager=off` to prevent `psql` from launching an interactive terminal pager (`less` or `more`) which hangs non-interactive subshells.
- Pass `-x` (expanded mode) when inspecting rows with wide columns (e.g. JSON payloads, long text, or logs).

```bash
# Query with pager disabled
psql "$PG_URL" -P pager=off -c "SELECT * FROM <table_name> LIMIT 5;"

# Query wide rows with vertical / expanded layout
psql "$PG_URL" -P pager=off -x -c "SELECT * FROM <table_name> ORDER BY 1 DESC LIMIT 1;"
```

### Diagnostic & Activity Queries

```bash
# Check active connections and running queries
psql "$PG_URL" -P pager=off -c "
  SELECT pid, usename, state, wait_event_type, wait_event, query 
  FROM pg_stat_activity 
  WHERE datname = current_database() AND state != 'idle';
"
```

> **Discoverability**: Run `psql --help` to explore client flags (`-t` for raw tuples, `-A` for unaligned CSV-style output, `-f` to run a SQL file).

---

## 2. Programmatic ORM & Migration Access

When working with Python backend services:

### Locating Models & DB Utilities
1. Inspect the service's database module (typically `app/db.py`) to discover how connections, engine lifecycle, session makers, and migrations (`init_db`) are implemented.
2. Inspect the service's model definitions (typically `app/models.py`) to verify current table names, column types, and schema relationships before querying.

### Health Check & Connectivity Probe
Verify database connectivity through the application's native database engine:

```bash
uv run python -c "
import asyncio
from app.db import check_db_health
print('Connected' if asyncio.run(check_db_health()) else 'Failed')
"
```

### Running Migrations / Schema Initialization
Run table creation and schema migrations defined in the codebase:

```bash
uv run python -c "
import asyncio
from app.db import init_db
asyncio.run(init_db())
print('Schema initialized successfully.')
"
```

### Dynamic Python Querying
To inspect records using the application's ORM:

```bash
uv run python -c "
import asyncio
from sqlmodel import select, text
from app.db import async_session

async def inspect():
    async with async_session() as session:
        # Run arbitrary SQL or query models discovered in app/models.py
        result = await session.execute(text('SELECT current_database(), current_user, version()'))
        print(result.fetchone())

asyncio.run(inspect())
"
```

---

## 3. Neon & Cloud PostgreSQL Troubleshooting

### Connection Pooling (`-pooler`)
- **Pooled Endpoints**: Neon connection strings containing `-pooler` in the hostname route through PgBouncer in transaction pooling mode.
- **NullPool Requirement**: In transaction pooling mode, prepared statements and persistent session-level state are not preserved across transactions. Python applications should use `NullPool` (e.g. `DB_USE_NULL_POOL=true`) to avoid connection reuse conflicts.
- **DDL / Migrations**: Run schema migrations or DDL statements against direct (unpooled) endpoints whenever possible.

### Channel Binding & SSL
- **SSL**: Serverless PostgreSQL requires TLS transport encryption (`ssl=require` or `sslmode=require`).
- **Channel Binding**: Some Neon connection strings include `channel_binding=require`. The `asyncpg` Python driver does not support SCRAM channel binding. If an `asyncpg driver does not support channel binding` error occurs, strip `channel_binding=require` from the connection string or set `ALLOW_UNBOUND_CHANNEL=true`. TLS encryption remains fully active.

### Pager Hangs
- If a `psql` command appears stuck or times out in the agent subshell, ensure `-P pager=off` or the environment variable `PAGER=cat` is set.
