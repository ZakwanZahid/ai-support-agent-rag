export type UUID = string;
export type ISODateString = string;

/**
 * One page of a keyset-paginated collection.
 *
 * `next_cursor` is opaque — it encodes a position in the server's sort order,
 * not an offset — so it is passed back untouched and never constructed here.
 * See docs/06-decisions.md, ADR-041.
 */
export interface Page<T> {
  items: T[];
  next_cursor: string | null;
  has_more: boolean;
}

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
