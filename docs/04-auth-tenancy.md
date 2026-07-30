# Authentication and Organization Access

## JWT Flow

Users register with an email and password through `POST /api/v1/auth/register`. Passwords are hashed before storage and API responses never expose `password_hash`. Login through `POST /api/v1/auth/login` verifies the supplied credentials and returns a short-lived JWT access token. Protected requests send that token as `Authorization: Bearer <token>`.

The access token contains the user's UUID in the standard `sub` claim plus issued-at and expiration timestamps. `GET /api/v1/auth/me` demonstrates the authenticated-user flow.

## Password Hashing

The backend uses `pwdlib` with its recommended Argon2 password hasher. Argon2 is deliberately expensive to slow offline password guessing. Plaintext passwords exist only long enough to validate or hash a request and are never persisted.

## Current User

`get_current_user` validates the Bearer token, parses its subject as a UUID, loads the user from PostgreSQL, and rejects missing, invalid, expired, unknown, or inactive identities with `401 Unauthorized`.

## Organization Context

Users and organizations have a many-to-many relationship through `organization_members`. Creating an organization adds the current user as its `owner`. Organization list queries join through membership, and individual organization requests require a matching membership.

Organization-aware dependencies take context from an `{organization_id}` path parameter when present, or from `X-Organization-Id` for future routes without an organization in the path. Missing context is a bad request. Both an unknown organization and a private organization belonging to someone else return the same `404` response, which avoids revealing private workspace IDs.

Every tenant-owned route must scope database operations by `organization_id`, even when another relation could identify the tenant. This mirrors the direct tenant key in the schema, reduces accidental cross-tenant queries, and prepares the application for PostgreSQL Row Level Security.

## Roles

Membership roles are `owner`, `admin`, and `member`. The reusable `require_role(["owner", "admin"])` dependency is ready for future management routes. Owners and admins will manage knowledge bases and documents; members will be able to chat. No document or RAG routes are implemented yet.

## Future Improvements

- Refresh-token rotation and revocation
- Email verification
- Password reset and account recovery
- Authentication and authorization audit logs
- Rate limiting and suspicious-login monitoring
- PostgreSQL Row Level Security policies
