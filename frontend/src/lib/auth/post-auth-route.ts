const DEFAULT_DESTINATION = "/dashboard";

/**
 * Where to send someone after a successful sign-in or registration.
 *
 * Honours the `returnTo` set by the API client when an expired session
 * interrupted a request, so users land back where they were. Only same-origin
 * paths are accepted; anything else falls back to the dashboard, so a crafted
 * link cannot use the login redirect to bounce someone off-site.
 */
export function resolvePostAuthDestination(): string {
  if (typeof window === "undefined") {
    return DEFAULT_DESTINATION;
  }

  const returnTo = new URLSearchParams(window.location.search).get("returnTo");
  if (!returnTo) {
    return DEFAULT_DESTINATION;
  }

  // A single leading slash means a path on this origin. "//evil.com" and
  // "https://evil.com" are both rejected.
  const isSameOriginPath =
    returnTo.startsWith("/") && !returnTo.startsWith("//");

  return isSameOriginPath ? returnTo : DEFAULT_DESTINATION;
}
