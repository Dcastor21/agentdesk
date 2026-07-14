# F01 — Project Scaffold & Deploy Loop

## Problem

Nothing exists yet. Before any pipeline, auth, or intelligence can be built, we need a deployable skeleton: a live API service on Render, the right directory layout, and a health endpoint that confirms the deploy loop works end-to-end. Every subsequent feature depends on this foundation being in place.

## Approach

Create a minimal async FastAPI app in `apps/api/`, a placeholder `apps/mcp/` directory (real MCP server is F10), and a `docs/` tree. Write a `render.yaml` that declares the `agentdesk-api` service, binds `$PORT`, and configures the `/health` health check. Containerize with a `Dockerfile` so Render's build is deterministic and matches local dev exactly.

## Decisions & why

| Decision | Why + what was rejected | Reversible? |
|---|---|---|
| FastAPI (async) as the API framework | Async-first matches the I/O-heavy LangGraph pipeline; Django REST rejected (sync by default, heavier); Flask rejected (no native async, no built-in validation) | Yes — framework swap is painful but possible |
| `pyproject.toml` + `uv` for dependency management | `uv` is the modern Python toolchain; `pip` + `requirements.txt` rejected (no lock-file guarantee, slower CI); Poetry rejected (slower resolver, heavier) | Yes |
| Dockerfile-based deploy on Render | Deterministic build; Render's native Python buildpack rejected (opaque behavior, harder to replicate locally) | Yes |
| `apps/api/` and `apps/mcp/` as top-level app dirs | Matches CLAUDE.md layout spec; monorepo root rejected (no separation when MCP server is added in F10) | Yes — dirs can be renamed |
| `apps/mcp/` committed as empty placeholder | Reserves the directory in git without building anything; skipping it entirely rejected (git ignores empty dirs, layout would be incomplete) | Yes |
| `CMD` in shell form for `$PORT` expansion | Render injects `$PORT` at runtime; exec-form CMD can't expand shell vars without an entrypoint wrapper; shell form is simpler for one env-var substitution | Yes |
| Dockerfile in `apps/api/`, not repo root | Keeps build context scoped to the API app; a root Dockerfile would bundle unrelated files and break when MCP is added | Yes |
| `render.yaml` at repo root, `dockerContext: apps/api` | Render reads `render.yaml` from root; `dockerContext` scopes the build to the API dir so only `apps/api/` is sent to the Docker daemon | Yes |
| `autoDeploy: true`, `branch: main` | Makes `git push origin main` the sole deploy trigger — no manual dashboard step; rejected always-on preview branches (not needed until multi-env is required) | Yes |
| `requirements.txt` for Docker deps, not `-e .` | `uv pip install -e .` triggers hatchling to build a wheel and requires a package dir named `agentdesk_api`; the app is a flat `main.py` script, not an installable package — `-r requirements.txt` installs deps without a build step | Yes |

## Done-when

- [x] Push to main → live `200` on Render's `/health` endpoint. ✓ confirmed 2026-07-14

---

## Recap

### What got done
- `apps/api/` scaffolded: `main.py` (async FastAPI, `/health`), `pyproject.toml`, `requirements.txt`, `Dockerfile`, `.dockerignore`
- `apps/mcp/.gitkeep` reserves the MCP directory without building anything (real server is F10)
- `render.yaml` at repo root: Docker build from `apps/api/`, `branch: main`, `autoDeploy: true`, `healthCheckPath: /health`
- `docs/features/F01-scaffold-deploy.md` (this file) tracking all decisions
- Deploy loop confirmed: `git push origin main` → Render build → live `200 /health`

### What we'd revisit
- `pyproject.toml` is present but not used by the Dockerfile (deps live in `requirements.txt`). Once the project grows, consider switching to `uv export --format requirements-txt` to keep a single source of truth, or restructuring as a proper package with a `src/` layout.
- The `master` branch still exists on the remote alongside `main` — worth deleting it to avoid confusion.

### Exact next step to resume cold
**F02 — Workspaces, auth & RLS tenancy.** Start with the Supabase project setup: create the `workspaces`, `users`, and `sessions` tables with RLS policies, then wire Clerk JWT verification into the FastAPI app as a dependency. Pair prompt: `/pair F02`.
