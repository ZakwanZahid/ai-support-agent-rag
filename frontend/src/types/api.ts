export type UUID = string;
export type ISODateString = string;

/** FastAPI's validation error entry, as returned inside a 422 `detail` array. */
export interface FastAPIValidationIssue {
  type: string;
  loc: Array<string | number>;
  msg: string;
  input?: unknown;
  ctx?: Record<string, unknown>;
}

/**
 * The backend returns FastAPI's native error shape rather than a custom
 * envelope. `detail` is a string for raised HTTPExceptions and an array of
 * issues for request validation failures; the API client normalizes both into
 * a single readable message. See docs/06-decisions.md.
 */
export interface FastAPIErrorBody {
  detail?: string | FastAPIValidationIssue[];
  message?: string;
}
