# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FreeUnit is the community LTS fork of NGINX Unit (upstream archived October 2025),
a polyglot application server in C that serves static assets and runs app code in
eight languages. Primary fork motivation: PHP 8.4/8.5+ support and continued
security maintenance. Upstream lineage is preserved — source files keep the `nxt_`
prefix and original NGINX/Igor Sysoev copyrights.

- Default PR branch: `master`. Conventional Commits, English (see `CONTRIBUTING.md`).
- Issue triage protocol (P0–P4 priority tiers) lives in `UNFREEZE.md`.

## Build & test — Docker only

**ALL build/test commands MUST run inside Docker.** Never run `./configure`,
`make`, `pytest-3`, or language runtimes directly on the host — host drift hides
bugs that surface only in CI. The runner builds a `freeunit-test:local` image
mirroring `pkg/docker/template.Dockerfile` and mounts the source as a volume, so
host edits are reflected immediately.

```bash
./test/run-local.sh                                          # full suite (~30 min)
./test/run-local.sh python php perl                          # specific module suites
./test/run-local.sh -t test_tls.py                           # one test file
./test/run-local.sh -t test_tls.py::test_tls_certificate_change   # one test function
./test/run-local.sh -n -t test_tls.py                        # dry-run (print, don't execute)
./test/run-local.sh --clang-ast                              # C-code AST quality check
docker rmi freeunit-test:local                               # force image rebuild after Dockerfile change
```

For a one-shot raw command, override the image's fixed `ENTRYPOINT` and mount at `/unit`:

```bash
docker run --rm --entrypoint bash -v "$(pwd):/unit" -w /unit freeunit-test:local -c '<cmd>'
```

Tests require **root** (Unit creates Unix sockets, network namespaces, cgroups);
isolation tests need `--privileged` or real root. The container builds with
`--tests --openssl --njs --zlib --zstd --brotli --otel`.

## Build system

The configurator is a hand-rolled POSIX-shell framework in `auto/` (NOT autotools).
`./configure` writes `build/Makefile` and `build/include/nxt_auto_config.h`; `make`
reads the generated Makefile. Core daemon options are in `auto/help`
(`--openssl`, `--njs`, `--otel`, `--zlib`/`--zstd`/`--brotli`, `--debug`, `--tests`, …).

Language modules are configured **separately** — `./configure <lang> [opts]` is
dispatched through `auto/modules/conf` to `auto/modules/<lang>`, then built with
`make <target>`:

```bash
./configure --openssl --otel && make          # core daemon (build/sbin/unitd)
./configure python --config=python3-config && make python3   # a module -> build/lib/unit/modules/*.so
./configure php && make php
```

Each module's `--help` is reachable via `./configure <lang> --help`.

## Architecture

Multi-process, shared-nothing design — understand the process roles before
tracing any request:

- **main process** (privileged, `nxt_main_process.c`) — forks and supervises all
  others; the only process that retains privileges (for `setuid`, namespaces, cgroups).
- **controller** (`nxt_controller.c`) — owns the RESTful JSON config API exposed on
  the control socket (default `unix:/var/run/control.unit.sock`). Config is applied
  with zero-downtime reconfiguration; validation is in `nxt_conf_validation.c`.
- **router** (`nxt_router.c`, `nxt_http_*.c`) — accepts connections, parses HTTP/1
  & HTTP/2 & WebSocket, runs routing/rewrite/static/proxy, and dispatches requests
  to app workers. Single point handling all client I/O.
- **app workers** — per-application processes (`nxt_process.c`, `nxt_isolation.c`)
  running user code via a language module, sandboxed with namespaces/cgroups/capabilities.

Cross-cutting layers:

- **libunit** (`src/nxt_unit.c`, `nxt_unit.h`) — the embedded library each language
  module links against. It speaks to the router over **ports** (`nxt_port_*.c`):
  message queues backed by shared memory (`nxt_port_memory.c`) plus a Unix-socket
  control channel. This is the request/response data path; the control socket is
  config-only.
- **Event engine** (`nxt_event_engine.c`) — pluggable async I/O (epoll/kqueue/etc.,
  selected in `auto/events`), the reactor under router and controller.
- **Memory** — pool allocator (`nxt_mp.c`), zone allocator (`nxt_mem_zone.c`); plus
  custom containers `nxt_lvlhsh` (lock-free hash), `nxt_rbtree`, `nxt_array`, `nxt_buf`.
- **tstr/var** (`nxt_tstr.c`, `nxt_var.c`) — templated strings / config variables
  (`$host`, `$uri`, …); njs (`nxt_js.c`) backs JavaScript expressions in config.

Layout: `src/` core C + per-language module subdirs (`python/`, `php/`, `perl/`,
`ruby/`, `java/`, `nodejs/`, `wasm/`); `go/` is the cgo-based Go module; `src/otel/`
and `src/wasm-wasi-component/` are Rust crates; `tools/unitctl/` is the Rust CLI;
`src/test/` holds C unit tests; `test/` holds the pytest suite.

## Test suite

Python/pytest under `test/`. Lifecycle fixtures and the `option` global live in
`test/conftest.py`; reusable helpers (HTTP clients, log assertions, status checks)
in `test/unit/`. Tests are `test_*.py` files / `test_*` functions; per-language app
fixtures sit in subdirs (`test/php/`, `test/go/`, …). `--restart` mode restarts Unit
between tests to catch state leakage (slower). `test_tls_certificate_change` can fail
on stale TLS state — re-run individually.

## Tools

- `tools/unitctl` — Rust CLI for managing Unit (generated partly from `docs/unit-openapi.yaml`).
- `tools/unitc` — curl wrapper around the control API (`unitc /config`, supports YAML via `yq`).
- `tools/setup-unit` — first-run install/welcome-page helper.

## MCP tooling

Two MCP servers back work in this repo — prefer them over blind `grep`/`Read`
sweeps across the large `nxt_*` C tree.

- **codegraph** (configured in `.mcp.json`) — SQLite knowledge graph of every
  symbol, edge, and file. Consult it BEFORE writing or editing code, not during.
  - "how does X work" / architecture / "where is X" / tracing a flow →
    `codegraph_explore` (PRIMARY; one capped call returns verbatim source of the
    relevant symbols grouped by file — usually the only call needed).
  - impact of a change → `codegraph_callers` / `codegraph_callees` /
    `codegraph_impact` (e.g. before touching a shared `nxt_port_*` or `nxt_mp_*`
    function, check what it breaks). The index lags writes by ~1s via the watcher.
- **agentmemory** (via the `local_1mcp` proxy — tools are exposed as
  `mcp__local_1mcp__agentmemory_1mcp_memory_*`) — persistent cross-session memory.
  Recall relevant project facts/decisions at the start of a task
  (`memory_recall` / `memory_smart_search`) and record durable, non-obvious
  findings (architecture decisions, gotchas, fork-specific deviations) as you go
  (`memory_save`). Do not store what the repo/git already records.

## Conventions

- C indent: 4 spaces; Makefiles use tabs; YAML 2 spaces (`.editorconfig`). Follow the
  existing `nxt_`-prefixed C style. Public C functions/modules get a comment header.
- The user's global naming/comment rules (see `~/.claude/CLAUDE.md`) apply to new code;
  match surrounding upstream style when editing existing `nxt_` files.
- API/config reference is `docs/unit-openapi.yaml`; user-facing changes are logged in
  `docs/changes.xml` (rendered to `CHANGES`).
