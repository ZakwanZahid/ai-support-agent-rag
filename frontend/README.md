# AI Support Agent RAG Frontend

Responsive Frontend v1 for the multi-tenant AI Support Agent RAG API. The application covers authentication, organization workspaces, knowledge bases, document ingestion and indexing, conversations, grounded chat answers, and source citations.

The UI uses the Next.js App Router and TypeScript. This repository's frontend commands run through the vinext build adapter, while pages and layouts use Next.js-compatible App Router conventions.

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
|-- app/                    # App Router layouts and routes
|   |-- (auth)/             # Login and register routes
|   `-- dashboard/
|       |-- knowledge-bases/
|       |-- documents/
|       |-- chat/
|       `-- conversations/
|-- src/
|   |-- components/
|   |   |-- providers.tsx  # TanStack Query and toast providers
|   |   |-- ui/            # Reusable shadcn/ui-style primitives
|   |   |-- layout/        # Dashboard shell and navigation
|   |   |-- common/        # Shared states, headings, and status UI
|   |   |-- chat/          # Messages, citations, and composer
|   |   |-- documents/     # Document views, upload, and actions
|   |   |-- kb/            # Knowledge-base cards and forms
|   |   `-- organizations/ # Organization creation
|   |-- hooks/              # Protected workspace and document actions
|   |-- lib/
|   |   |-- api/           # Typed Axios API modules
|   |   |-- auth-token.ts  # MVP browser token storage
|   |   |-- query-keys.ts  # Tenant-aware query keys
|   |   `-- utils.ts
|-- .env.example
|-- package.json
`-- README.md
```

The exact route tree is described in [`../docs/10-frontend-v1.md`](../docs/10-frontend-v1.md).

## API Integration

The frontend calls the existing API through modules under `src/lib/api/`:

- `client.ts`: Axios instance, API origin, bearer token, common errors, and `401` handling
- `auth.ts`: register, login, and current user
- `organizations.ts`: list and create organizations
- `knowledge-bases.ts`: organization-scoped knowledge-base operations
- `documents.ts`: upload, list/detail, ingest, and index operations
- `conversations.ts`: create/list conversations, load messages, and send RAG questions

The selected organization ID is included in all tenant-owned request paths. The UI helps users stay in one workspace, but FastAPI remains responsible for membership authorization and tenant isolation.

## Authentication

Frontend v1 stores the backend access token in browser `localStorage`. The shared API client attaches it as a bearer token, clears it after an unauthorized response, and routes the browser back to login when practical.

This is an explicit MVP compromise. A production version should move authentication to `Secure`, `HttpOnly` cookies with appropriate same-site and CSRF protection.

## Common Troubleshooting

### The browser reports a network or CORS error

- Confirm FastAPI is running at the exact `NEXT_PUBLIC_API_BASE_URL`.
- Keep the default free of a trailing `/api/v1`.
- Confirm backend `FRONTEND_ORIGIN` is `http://localhost:3000`.
- Restart the frontend process after changing `.env.local`; public environment variables are loaded when the app starts.

### Requests return `401 Unauthorized`

The token may be missing or expired. Log out, log in again, and confirm the browser has not blocked `localStorage`. The client intentionally clears a rejected token.

### No organization data appears

Create an organization from the application first, then select it in the top bar. Knowledge bases, documents, and conversations are scoped to the active organization.

### A document cannot be indexed

The normal lifecycle is:

```text
pending -> processing -> processed -> indexed
```

Ingest before indexing. If status becomes `failed`, inspect the readable UI error and backend logs. Indexing requires a valid backend OpenAI key; the key does not belong in the frontend environment.

### Chat returns no citations

Confirm the selected knowledge base contains an indexed document and that the question is answerable from its text. The safe insufficient-context answer correctly returns no citations.

### Port 3000 is already in use

Stop the process using the port or start the frontend on an available port supported by the local adapter. If the origin changes, also update the backend's development CORS allowlist.

### Install or build fails unexpectedly

- Verify `node --version` satisfies the version in `package.json`.
- Run `npm install` from `frontend/`.
- Run `npm run typecheck` first for the most direct TypeScript diagnostics.
- Do not delete the lockfile as a first troubleshooting step; it keeps dependency versions reproducible.

## More Documentation

- [Frontend v1 design and manual test flow](../docs/10-frontend-v1.md)
- [RAG chat and citations](../docs/09-rag-chat.md)
- [Architecture decisions](../docs/06-decisions.md)
- [Repository setup](../README.md)
