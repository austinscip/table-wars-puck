# ADR 0007 — Fleet-Scale DB Connections via the Transaction Pooler

**Status:** Accepted
**Date:** 2026-06-05

## Context

Each venue's Flask box writes to Supabase as the `postgres` role over
`DATABASE_URL` (`SupabaseWriter`), in production via a `psycopg_pool`
connection pool. That pool connects **directly to Postgres** (port 5432).
At one bar that's a handful of connections; across a chain it's fatal —
**100 venues × a client pool of N** blows past Postgres's connection ceiling
(a few hundred backends). Direct connections don't scale to a fleet.

Supabase's answer is the **transaction pooler** (Supavisor / pgbouncer in
transaction mode, port **:6543**): the server multiplexes many client
connections onto few Postgres backends, checking a backend out **per
transaction** rather than per session. The catch the handoff flags: it
"breaks session features." Concretely, what actually breaks in transaction
mode is **server-side prepared statements** — psycopg3 prepares a statement
after a few executions, but in transaction mode the next execution may land
on a different backend that never saw the PREPARE. Session GUCs, advisory
locks held across statements, `LISTEN/NOTIFY`, and `WITH HOLD` cursors break
too — but `SupabaseWriter` uses none of them. Notably `create_match`'s
`with conn.transaction()` is **fine**: a single transaction is exactly the
unit the pooler multiplexes.

Part (b) of the gap — high write/broadcast volume from per-input snapshot
writes + Realtime fan-out — is already addressed by ADR 0004: the
`PersistenceQueue` coalesces snapshots and drains them asynchronously, and
the TV renders local-first so it no longer depends on Realtime fan-out for
gameplay. So this ADR is about (a), the connection model.

## Decision

**Route fleet traffic through the transaction pooler, and make
`SupabaseWriter` transaction-pooler-safe — chiefly by disabling server-side
prepared statements when the DSN targets it.**

- `_is_transaction_pooler(dsn)` detects the pooler by the `:6543` port (or
  an explicit `PGBOUNCER_TRANSACTION_MODE=1` override), so ops flip it by
  pointing `DATABASE_URL` at the pooler endpoint — **no code change**.
- For pooler connections, `_conn_kwargs` sets `prepare_threshold=None`
  (psycopg3: never use server-side prepared statements). Direct (:5432)
  connections keep prepared statements for speed. Applied uniformly to both
  the direct-connect and pooled paths.
- The client pool is **capped small** (≤4) in pooler mode: the pooler does
  the real multiplexing, so a large per-box client pool is both unnecessary
  and actively harmful (it multiplies backend pressure across the fleet).
- Everything else is unchanged. The method bodies, transactions, and RLS
  bypass (connecting as `postgres`) are identical; only the connection
  config differs.

## Consequences

- A venue box now opens a few client connections to the pooler instead of
  direct Postgres backends; the fleet scales to many venues without
  exhausting the backend ceiling.
- Losing server-side prepared statements costs a little per-query planning
  time on the pooler path. For our small, varied write mix (one transaction
  per match event) that's negligible, and it's the price of pooler
  compatibility.
- Anything added later that needs **session** semantics (advisory locks held
  across statements, `LISTEN/NOTIFY`, temp tables, multi-statement
  prepared-cursor work) must NOT assume the transaction pooler — use a
  direct connection (or Supabase's *session* pooler, :5432) for that path,
  and document why. The runtime's existing Redis-based distributed lock is
  the right primitive for cross-worker locking, not Postgres advisory locks.
- Detection is by port/override, so dev (direct local Postgres) keeps
  prepared statements and full session features automatically; only
  pooler-targeted DSNs change behaviour.
