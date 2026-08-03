export type UUID = string;
export type ISODateString = string;

export interface FastAPIValidationIssue {
  type: string;
  loc: Array<string | number>;
  msg: string;
  input?: unknown;
  ctx?: Record<string, unknown>;
}

export interface FastAPIErrorBody {
  detail?: string | FastAPIValidationIssue[];
  message?: string;
}
