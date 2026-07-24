# Architectural Decision Records (ADRs)

This document registers the key architectural decisions and technical trade-offs made during the design and development of the Real-Time Collaborative Platform.

---

## ADR 1: CRDT vs. Operational Transformation (OT)

### Context & Problem
We needed a synchronization model that converges reliably under concurrent, conflicting edits from multiple clients (humans and AI) editing the same document.

### Decision
We chose **Conflict-Free Replicated Data Types (CRDTs)**, implemented via the Rust-backed `pycrdt` library (compatible with Yjs), rather than building or using an Operational Transformation (OT) engine.

### Rationale & Trade-offs
* **Decentralization:** Unlike OT, which requires a central, stateful server to sequence operations and rewrite incoming transforms based on history, CRDTs merge mathematically without a single source of truth.
* **Performance:** `pycrdt` is built on top of `yrs` (the Rust port of Yjs), which offers extremely fast serialization, delta compression, and sub-millisecond document sync times.
* **Offline Capability:** CRDT updates can be applied out-of-order and will still converge. This allows clients to reconnect, apply queued updates, and merge states without complex rewrite logic.

### Scaling & Failure Modes
* **Memory Overhead (Tombstones):** Because CRDTs retain a history of mutations and tombstones for deleted characters to resolve potential sync conflicts, the in-memory size of a long-lived document grows monotonically. For documents with hundreds of thousands of edits, memory usage on both client and server will scale linearly, leading to performance degradation.
* **Initial Connection Synchronization:** When a client first connects, it must fetch the entire document state. A massive edit history translates to large binary updates, increasing the initial download payload and time-to-interactive for slow networks.
* **CPU-Bound Merges:** Parsing and merging large state updates on low-powered client devices (like mobile browsers) can temporarily freeze the main thread.

---

## ADR 2: AI as a First-Class Concurrent Editor

### Context & Problem
Many collaborative tools implement AI as a "sidebar chat" or a blocking state-overwrite. We wanted the AI agent to edit the document concurrently alongside humans.

### Decision
We decided to treat the AI agent as a **first-class actor** in the CRDT event stream. We integrated Google Diff-Match-Patch to translate the AI's raw string responses into atomic Yjs character-level mutations.

### Rationale & Trade-offs
* **Preserving Cursors:** If the AI simply overwrote the document text (`ytext.delete()` followed by `ytext.insert()`), all concurrent users' active cursor selections would be wiped. 
* **Character Diffs:** By executing character-level diffing on the server, we generate minimal insertions and deletions. The AI's changes are applied inside a single transactional block:
  ```python
  with doc.transaction():
      # diff-match-patch minimal modifications
  ```
  This integrates the AI edits seamlessly into Yjs, preserving active concurrent cursors nearby.

### Scaling & Failure Modes
* **Diffing Performance Bottleneck:** Diff-Match-Patch operates with $O(ND)$ time complexity where $N$ is document length and $D$ is edit distance. For large files, executing this on every AI turn is highly CPU-bound and will block the server's event loop, impacting other connected clients.
* **Syntactic Edit Collisions:** Concurrently editing the same paragraph as a human user can cause Diff-Match-Patch to resolve the merge in semantically or syntactically broken ways, interleaving character changes awkwardly.
* **API Rate Limits and Token Inflation:** Constant real-time triggers for AI completions over long documents will spike token consumption and hit LLM provider rate limits quickly.

---

## ADR 3: Hybrid Persistence Strategy (Strategy C)

### Context & Problem
We needed a database persistence layer to survive server restarts, but writing the full state on every keypress causes massive write amplification, while saving only snapshots destroys history.

### Decision
We implemented a **Hybrid Snapshotting + Operation Log** storage pattern (Strategy C).

```
document_updates (Op Log)   ──►  Append on every WebSocket edit (Tag 0)
document_snapshots (Snaps)  ──►  Write full YDoc state on every 5th edit (threshold)
```

### Rationale & Trade-offs
* **Performance & Revision History:** We store every incremental binary update in `document_updates` to retain a full transaction audit trail.
* **Optimized Load Times:** Loading a document doesn't require playing back millions of updates from the beginning of time. Instead, the server loads the *latest snapshot* and plays back only the few updates created *after* that snapshot's timestamp.

### Scaling & Failure Modes
* **I/O Spikes during Snapshotting:** Saving the full YDoc state every 5th edit causes database write spikes. Under high concurrency across many documents, concurrent snapshot operations can saturate database connection pools.
* **Op Log Bloat & Startup Latency:** If snapshot writing fails or if the threshold is too high, the incremental log (`document_updates`) accumulates thousands of operations. Upon document load, replaying a bloated log on top of the base snapshot introduces significant latency.
* **State Drift/Split-Brain:** If the in-memory state is mutated but database serialization (snapshots or logs) fails due to transient connection errors, the persisted document diverges from active client states, resulting in potential data loss on server restarts.

---

## ADR 4: Custom Byte-Framing Protocol

### Context & Problem
We needed to send both collaborative document states (which are binary CRDT byte-arrays) and ephemeral presence information (like active user cursors and usernames) over a single WebSocket channel.

### Decision
We designed a lightweight **Byte-Framing Protocol** where every WebSocket message is prepended with a single control byte:
* `b"\x00"` (Sync Tag): Indicates binary Yjs CRDT update packets. Applied to the server YDoc and written to the database.
* `b"\x01"` (Presence Tag): Indicates ephemeral cursor/color payloads. Dispatched directly to other clients without DB storage.

### Rationale & Trade-offs
* **No Database Pollution:** Presence data changes on every cursor movement. Relaying it directly (bypassing the DB) prevents writing thousands of useless cursor coordinates to disk.
* **Unified Pipeline:** Using one WebSocket port instead of multiple sockets or polling endpoints simplifies connection management and reduces client-side connection overhead.

### Scaling & Failure Modes
* **Head-of-Line Blocking:** Ephemera (presence packets like cursor movements) and sync updates share the same WebSocket channel. A burst of cursor updates from multiple users can clog the TCP send buffer, delaying critical CRDT sync messages.
* **Broadcast Storms:** Ephemeral cursor updates are broadcasted to all connected clients, scaling at $O(N^2)$ message volume where $N$ is the number of active users. A highly populated document will rapidly saturate network bandwidth and server CPU.
* **Client Buffer Saturation:** Slow clients might fail to process high-frequency cursor coordinates, causing browser memory usage to balloon and connection dropouts.
