# SupportMind Frontend

The web interface for the multi-tenant AI support API: landing page, guided onboarding, dashboard, knowledge spaces, documents, grounded chat with sources, chat threads, and workspace settings.

Built with the Next.js App Router and TypeScript, using the standard Next.js CLI. The interface deliberately does not expose the API's vocabulary; see [Frontend Redesign](../docs/10-frontend-redesign.md) for the terminology mapping and the reasoning behind it.

## Requirements

- Node.js 22.13 or newer
- npm
- The FastAPI backend and PostgreSQL database running locally
- A backend `OPENAI_API_KEY` for document indexing and RAG answers

## Install

From the repository root:

```powershell
cd frontend
npm install
```

Dependencies include Tailwind CSS, TanStack Query, Axios, React Hook Form, Zod, Radix-backed shadcn/ui-style primitives, Lucide icons, and Sonner.

## Environment Setup

Create the local frontend environment file:

```powershell
Copy-Item .env.example .env.local
```

Default value:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

`NEXT_PUBLIC_API_BASE_URL` must be the origin of the running FastAPI service, without `/api/v1` appended. API modules add their own versioned paths.

Never place `OPENAI_API_KEY`, database credentials, JWT signing keys, or other secrets in this file. Values prefixed with `NEXT_PUBLIC_` are included in browser code.

## Run Locally

Start the backend first, then run:

```powershell
npm run dev
```

Open `http://localhost:3000`.

The development command is a persistent server. Stop it with `Ctrl+C` when finished. Use the bounded verification commands below in scripts and CI rather than waiting on the development server.

## Quality Checks

Run each command from `frontend/`:

```powershell
npm run typecheck
npm run lint
npm run build
```

- `typecheck` validates TypeScript without emitting files.
- `lint` runs ESLint.
- `build` creates a production build and catches route/build-time errors.

After a successful build, run the built application locally with:

```powershell
npm run start
```

## Project Structure

```text
frontend/
|-- app/                       # App Router layouts and routes
|   |-- page.tsx               # Marketing landing page
|   |-- (auth)/                # Login and register
|   |-- onboarding/            # Four-step guided setup
|   `-- dashboard/
|       |-- knowledge/         # Knowledge spaces list and detail
|       |-- documents/         # All documents, table and cards
|       |-- chat/              # Ask AI
|       |-- conversations/     # Chat threads list and detail
|       `-- settings/
|-- src/
|   |-- components/
|   |   |-- providers.tsx      # TanStack Query, auth, and toast providers
|   |   |-- ui/                # shadcn/ui-style primitives
|   |   |-- layout/            # App shell, sidebar, top bar, workspace switcher
|   |   |-- marketing/         # Landing page sections
|   |   |-- onboarding/        # Flow, stepper, and step components
|   |   |-- dashboard/         # Checklist, stats, recent items, quick actions
|   |   |-- knowledge/         # Knowledge space cards and dialog
|   |   |-- documents/         # Dropzone, status timeline, table, cards, actions
|   |   |-- chat/              # Messages, sources, composer, thread list
|   |   |-- settings/          # Workspace settings and placeholders
|   |   `-- common/            # Page header, empty, error, loading, status badge
|   |-- hooks/                 # Workspace, documents, chat, dashboard, preparation
|   |-- lib/
|   |   |-- api/               # Typed Axios API modules
|   |   |-- auth/              # Token storage, auth context, post-auth routing
|   |   |-- terminology.ts     # Backend-to-product vocabulary, single source
|   |   |-- query-keys.ts      # Tenant-aware query keys
|   |   `-- utils.ts
|   `-- types/                 # Domain types named for product concepts
|-- .env.example
|-- package.json
`-- README.md
```

`lib/terminology.ts` is worth reading first: it defines every user-facing status label, its badge tone, its position in the preparation timeline, and whether the UI should keep polling. Components derive those from it rather than mapping status strings themselves.

## API Integration

The frontend calls the existing API through modules under `src/lib/api/`:

- `client.ts`: Axios instance, API origin, bearer token, common errors, and `401` handling
- `auth.ts`: register, login, and current user
- `organizations.ts`: list, create, and rename organizations
- `knowledge-bases.ts`: organization-scoped knowledge-base operations
- `documents.ts`: upload, list/detail, and `prepare` (extraction plus indexing in one call); `ingest` and `index` remain for single-phase use
- `conversations.ts`: create/list conversations, load messages, and send RAG questions

The selected organization ID is included in all tenant-owned request paths. The UI helps users stay in one workspace, but FastAPI remains responsible for membership authorization and tenant isolation.

## Authentication

The frontend stores the backend access token in browser `localStorage`. The shared API client attaches it as a bearer token, clears it after an unauthorized response, and routes the browser back to login when practical.

This is an explicit MVP compromise. A production version should move authentication to `Secure`, `HttpOnly` cookies with appropriate same-site and CSRF protection.

## Common Troubleshooting

### The browser reports a network or CORS error

- Confirm FastAPI is running at the exact `NEXT_PUBLIC_API_BASE_URL`.
- Keep the default free of a trailing `/api/v1`.
- Confirm backend `FRONTEND_ORIGIN` is `http://localhost:3000`.
- Restart the frontend process after changing `.env.local`; public environment variables are loaded when the app starts.

### Requests return `401 Unauthorized`

The token may be missing or expired. Log out, log in again, and confirm the browser has not blocked `localStorage`. The client intentionally clears a rejected token.

### No workspace data appears

A new account is routed into onboarding, which creates a workspace and a knowledge space. If you skipped it, create a workspace from the switcher in the top bar. Knowledge spaces, documents, and chat threads are all scoped to the active workspace.

### A document never becomes Ready

The lifecycle shown in the UI is:

```text
Uploaded -> Processing -> Extracted -> Ready
```

which maps to `pending -> processing -> processed -> indexed` in the API. "Prepare for chat" runs the whole sequence server-side, so there is nothing to trigger manually. If it stops at Failed, the UI shows the backend's reason and offers a retry. Reaching Ready requires a valid backend `OPENAI_API_KEY`; that key does not belong in the frontend environment.

Note that `AUTO_INGEST_ON_UPLOAD` should stay `false`. With it enabled, upload starts extraction on its own and the subsequent prepare call conflicts with work already running, leaving the document stalled after extraction.

### Chat returns no sources

Confirm the selected knowledge space contains a Ready document and that the question is answerable from its text. Only knowledge spaces with at least one Ready document are selectable. The safe insufficient-context answer correctly returns no sources.

### Port 3000 is already in use

Stop the process using the port, or run `npm run dev -- -p 3001`. If the origin changes, update `FRONTEND_ORIGIN` in the backend environment so its development CORS allowlist matches.

### Routes 404, or the UI stops updating mid-flow, after running a build

`next build` and `next dev` both write to `.next`. Running a build while the dev
server is up corrupts its state: route groups start returning 404, and pages
stop reacting to data. It looks like an application bug and is not one.

Stop the dev server, `rm -rf .next`, then start it again. This is also why
`npm run build` immediately before `npm run test:e2e` can fail the end-to-end
test against an otherwise healthy backend.

### Install or build fails unexpectedly

- Verify `node --version` satisfies the version in `package.json`.
- Run `npm install` from `frontend/`.
- Run `npm run typecheck` first for the most direct TypeScript diagnostics.
- Do not delete the lockfile as a first troubleshooting step; it keeps dependency versions reproducible.

## More Documentation

- [Frontend redesign, terminology, and known limitations](../docs/10-frontend-redesign.md)
- [RAG chat and citations](../docs/09-rag-chat.md)
- [Architecture decisions](../docs/06-decisions.md)
- [Repository setup](../README.md)
