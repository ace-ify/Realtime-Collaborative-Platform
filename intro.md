# Real-Time Collaborative Backend (Google Docs-lite) with an AI Co-Editor

## Status
Planning / Not started

## One-line pitch
A backend for a collaborative document editor where multiple humans — and one AI agent — can edit the same document concurrently, with correct conflict resolution for all of them. The AI co-editor isn't a gimmick: it forces you to treat AI writes as just another concurrent actor, which is a genuinely novel angle most portfolios don't have.

## Problem it solves
Real-time applications require a fundamentally different architecture than request-response APIs: WebSockets, event-driven programming, state synchronization across multiple clients, and the concurrency problems that come with all of it. Adding an AI agent as a concurrent editor (not just a chat sidebar) means your conflict-resolution logic has to be genuinely correct, not just "good enough for two humans who rarely collide."

## Tech stack
- **API/realtime layer:** Python, FastAPI with WebSocket support (or a dedicated realtime layer if needed)
- **Conflict resolution:** CRDT library (e.g. Yjs-compatible approach, or a Python CRDT implementation) — alternative: build a simplified Operational Transform (OT) engine to show you understand the algorithm from first principles
- **State store:** PostgreSQL for document snapshots and history; Redis for active session/presence state
- **Pub/sub:** Redis pub/sub (or a message broker) for fanning out edits to all connected clients
- **AI agent:** calls into an LLM to propose edits (e.g. "improve this paragraph," "fix grammar in this section") that get applied as just another set of operations in the CRDT/OT stream

## Architecture overview
```
Client A ─┐
Client B ─┼─→ WebSocket Gateway → Redis pub/sub (fan-out)
AI agent ─┘         ↕                    ↕
              CRDT/OT engine      Presence tracking
                     ↕
          Postgres (document snapshots + operation log)
```

## Build phases

### Phase 1 — Basic realtime sync (week 1)
- WebSocket connections per document, broadcast raw edits to all connected clients
- No conflict resolution yet — establish the plumbing first (connect, disconnect, broadcast)

### Phase 2 — Conflict resolution (week 1-2) — the core of the project
- Implement CRDT-based or OT-based merging so concurrent edits from multiple clients converge to the same correct state
- Test with simulated concurrent edits (two clients editing the same line at the same time)

### Phase 3 — Presence and awareness (week 2)
- Track which users are connected and where their cursor is
- Handle disconnect/reconnect gracefully (client rejoins mid-document without losing state)

### Phase 4 — AI co-editor (week 2-3)
- The AI agent watches the document (or is invoked on demand), proposes an edit, and that edit is submitted through the *same* CRDT/OT pipeline as a human edit — not as a special-cased overwrite
- Handle the case where a human edits the same region the AI is mid-edit on: your conflict resolution must treat this exactly like a human-human conflict

### Phase 5 — Persistence and history (week 3-4)
- Periodic snapshotting to Postgres so documents survive server restarts
- Operation log for "time travel" / undo history
- Load test with many simulated concurrent clients; report latency and convergence time

## Key architecture decisions to document (ADRs)
- [ ] CRDT vs. OT — which you chose and why
- [ ] How the AI agent's edits are represented (as first-class operations, not special-cased)
- [ ] Snapshotting strategy (frequency, storage format)
- [ ] Reconnect/resync strategy for clients that drop and rejoin

## Metrics to capture and publish in the README
- Convergence time after N concurrent conflicting edits
- WebSocket connection handling under load (concurrent clients per document)
- Snapshot/persistence latency
- AI co-editor edit acceptance/conflict rate

## Interview talking points
- "How do you guarantee two clients editing the same line converge to the same result?"
- "What happens when a client disconnects mid-edit and reconnects?"
- "Why treat the AI agent's edits the same way as a human's, instead of special-casing them?"
- "CRDT vs OT — what's the tradeoff and why did you pick yours?"

## Stretch goals
- Multi-document support with sharding of WebSocket connections across instances
- Replace the simplified CRDT with a battle-tested library and document the migration reasoning
