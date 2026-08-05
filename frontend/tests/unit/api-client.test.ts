import { AxiosError, AxiosHeaders } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  APIError,
  getAPIErrorMessage,
  isAPIError,
  normalizeAPIError,
} from "@/lib/api/client";
import { locationAssign } from "../setup";

/** Builds an AxiosError shaped the way the real client receives one. */
function axiosErrorWith(status: number, data: unknown): AxiosError {
  const error = new AxiosError("Request failed");
  error.response = {
    status,
    data,
    statusText: "",
    headers: new AxiosHeaders(),
    config: { headers: new AxiosHeaders() },
  };
  return error;
}

/**
 * The API client is the only place FastAPI's error shapes are interpreted.
 * If it regresses, every error message in the product degrades to raw JSON or
 * a generic string, so these cover the shapes the backend actually returns.
 */
describe("normalizeAPIError", () => {
  it("uses a plain string detail from a raised HTTPException", () => {
    const error = normalizeAPIError(
      axiosErrorWith(409, { detail: "Document is already being prepared" }),
    );

    expect(error).toBeInstanceOf(APIError);
    expect(error.status).toBe(409);
    expect(error.message).toBe("Document is already being prepared");
  });

  it("flattens FastAPI's 422 validation array into one readable line", () => {
    const error = normalizeAPIError(
      axiosErrorWith(422, {
        detail: [
          { type: "string_too_short", loc: ["body", "name"], msg: "Field required" },
          { type: "value_error", loc: ["body", "email"], msg: "Invalid email" },
        ],
      }),
    );

    // "body" is dropped because it is an artefact of where the value came
    // from, not something a user can act on.
    expect(error.message).toBe("name: Field required; email: Invalid email");
    expect(error.message).not.toContain("body");
  });

  it("falls back to a status-specific message when there is no detail", () => {
    expect(normalizeAPIError(axiosErrorWith(413, {})).message).toContain(
      "too large",
    );
    expect(normalizeAPIError(axiosErrorWith(415, {})).message).toContain(
      "not supported",
    );
    expect(normalizeAPIError(axiosErrorWith(502, {})).message).toContain(
      "AI provider",
    );
  });

  it("explains an unreachable API rather than surfacing a network error", () => {
    const offline = new AxiosError("Network Error");
    offline.response = undefined;

    const error = normalizeAPIError(offline);

    expect(error.status).toBeNull();
    expect(error.message).toContain("Unable to reach the API");
  });

  it("distinguishes a cancelled request from a failure", () => {
    const cancelled = new AxiosError("canceled");
    cancelled.code = "ERR_CANCELED";
    cancelled.response = undefined;

    expect(normalizeAPIError(cancelled).message).toBe("The request was canceled.");
  });

  it("treats any 5xx as a server-side problem", () => {
    expect(normalizeAPIError(axiosErrorWith(503, {})).message).toContain(
      "server could not complete",
    );
  });

  it("passes an existing APIError through unchanged", () => {
    const original = new APIError("Already normalized", 400);
    expect(normalizeAPIError(original)).toBe(original);
  });

  it("handles non-axios errors and unknown values", () => {
    expect(normalizeAPIError(new Error("boom")).message).toBe("boom");
    expect(normalizeAPIError("just a string").message).toContain(
      "Something went wrong",
    );
    expect(normalizeAPIError(null).status).toBeNull();
  });

  it("never returns an empty message", () => {
    // An empty string would render as a blank error alert, which reads as a
    // broken UI rather than a failure.
    const cases = [
      axiosErrorWith(400, { detail: "" }),
      axiosErrorWith(400, {}),
      axiosErrorWith(404, { detail: [] }),
      new Error(""),
      undefined,
    ];

    for (const value of cases) {
      expect(normalizeAPIError(value).message.trim().length).toBeGreaterThan(0);
    }
  });

  it("exposes helpers used by components", () => {
    const error = axiosErrorWith(404, { detail: "Document not found" });
    expect(getAPIErrorMessage(error)).toBe("Document not found");
    expect(isAPIError(normalizeAPIError(error))).toBe(true);
    expect(isAPIError(new Error("plain"))).toBe(false);
  });
});

describe("token handling", () => {
  beforeEach(() => {
    vi.resetModules();
    window.localStorage.clear();
  });

  it("attaches the stored token as a bearer header", async () => {
    const { setAccessToken } = await import("@/lib/auth/token");
    const { apiClient } = await import("@/lib/api/client");
    setAccessToken("token-123");

    // Run the request interceptor directly; it is the only thing that decides
    // whether a call is authenticated.
    const handler = apiClient.interceptors.request as unknown as {
      handlers: Array<{ fulfilled: (c: unknown) => { headers: AxiosHeaders } }>;
    };
    const config = handler.handlers[0].fulfilled({
      headers: new AxiosHeaders(),
    });

    expect(config.headers.Authorization).toBe("Bearer token-123");
  });

  it("sends no Authorization header when signed out", async () => {
    const { apiClient } = await import("@/lib/api/client");

    const handler = apiClient.interceptors.request as unknown as {
      handlers: Array<{ fulfilled: (c: unknown) => { headers: AxiosHeaders } }>;
    };
    const config = handler.handlers[0].fulfilled({
      headers: new AxiosHeaders(),
    });

    expect(config.headers.Authorization).toBeUndefined();
  });

  it("clears the token when the API rejects the session", async () => {
    const { setAccessToken, getAccessToken } = await import("@/lib/auth/token");
    // resetModules gives this block a fresh module instance, so APIError has
    // to come from the same import or the class identities differ.
    const { apiClient, APIError: FreshAPIError } = await import(
      "@/lib/api/client"
    );
    setAccessToken("expired-token");

    const handler = apiClient.interceptors.response as unknown as {
      handlers: Array<{ rejected: (e: unknown) => Promise<unknown> }>;
    };

    await expect(
      handler.handlers[0].rejected(axiosErrorWith(401, { detail: "Expired" })),
    ).rejects.toBeInstanceOf(FreshAPIError);

    // Leaving a rejected token in storage would keep the app looking signed in
    // while every request failed.
    expect(getAccessToken()).toBeNull();

    // The user is sent to login carrying where they were, so signing back in
    // returns them there instead of dumping them on the dashboard.
    expect(locationAssign).toHaveBeenCalledOnce();
    expect(locationAssign.mock.calls[0][0]).toContain("/login?returnTo=");
  });

  it("keeps the token when the failure is not an auth failure", async () => {
    const { setAccessToken, getAccessToken } = await import("@/lib/auth/token");
    const { apiClient, APIError: FreshAPIError } = await import(
      "@/lib/api/client"
    );
    setAccessToken("valid-token");

    const handler = apiClient.interceptors.response as unknown as {
      handlers: Array<{ rejected: (e: unknown) => Promise<unknown> }>;
    };

    await expect(
      handler.handlers[0].rejected(axiosErrorWith(500, {})),
    ).rejects.toBeInstanceOf(FreshAPIError);

    expect(getAccessToken()).toBe("valid-token");
  });
});
