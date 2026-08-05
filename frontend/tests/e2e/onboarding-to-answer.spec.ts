import { expect, test } from "@playwright/test";

/**
 * The path the product exists to deliver: a new visitor arrives, signs up, is
 * guided through setup, uploads a document, waits for it to become answerable,
 * asks a question, and gets an answer with the passage it came from.
 *
 * Every assertion is written against what the user sees. If this spec ever has
 * to mention ingestion, indexing, or a raw status string to pass, the
 * redesign's core rule has regressed.
 *
 * Requires the backend, its database, and a working OPENAI_API_KEY.
 */

const SAMPLE_POLICY = `Refund Policy

Customers may request a full refund within 30 days of delivery, provided the
item is unused and in its original packaging. Refund requests are reviewed
within two business days. Approved refunds are returned to the original
payment method and typically appear within five business days.

Shipping Policy

Standard shipping takes three to five business days. Express shipping arrives
the next business day when ordered before 2pm.`;

function uniqueEmail(): string {
  return `e2e-${Date.now()}-${Math.floor(Math.random() * 1000)}@example.com`;
}

test("a new user can go from signup to a sourced answer", async ({ page }) => {
  const email = uniqueEmail();

  await test.step("the landing page explains the product before asking for an account", async () => {
    await page.goto("/");
    await expect(
      page.getByRole("heading", {
        name: /turn your support docs into an ai assistant/i,
      }),
    ).toBeVisible();
    await page.getByRole("link", { name: /get started/i }).first().click();
    await expect(page).toHaveURL(/\/register/);
  });

  await test.step("registering routes into onboarding, not an empty dashboard", async () => {
    await page.getByLabel(/full name/i).fill("E2E Tester");
    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel(/password/i).fill("testpassword123");
    await page.getByRole("button", { name: /create account/i }).click();

    await expect(page).toHaveURL(/\/onboarding/, { timeout: 30_000 });
    await expect(
      page.getByRole("heading", { name: /create your workspace/i }),
    ).toBeVisible();
  });

  await test.step("step 1 creates a workspace", async () => {
    await page.getByLabel(/workspace name/i).fill("E2E Retail");
    await page.getByRole("button", { name: /continue/i }).click();
  });

  await test.step("step 2 asks what the assistant will help with", async () => {
    await expect(
      page.getByRole("heading", { name: /what will this assistant help with/i }),
    ).toBeVisible();
    await page.getByRole("radio", { name: /customer support/i }).click();
    await page.getByRole("button", { name: /continue/i }).click();
  });

  await test.step("step 3 uploads a document and prepares it in one action", async () => {
    await expect(
      page.getByRole("heading", { name: /add your first document/i }),
    ).toBeVisible();

    await page.setInputFiles('input[type="file"]', {
      name: "refund-policy.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(SAMPLE_POLICY),
    });

    // The user is shown progress in product language. "Prepare for chat" is
    // one action; there is no separate ingest or index control to click.
    await expect(page.getByText(/prepare for chat/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /^ingest$/i })).toHaveCount(0);
    await expect(page.getByRole("button", { name: /^index$/i })).toHaveCount(0);
  });

  await test.step("preparation finishes and the flow advances on its own", async () => {
    // Embedding the document takes real time; the timeline advances to Ready
    // and the flow moves to the question step without the user acting.
    await expect(
      page.getByRole("heading", { name: /ask your first question/i }),
    ).toBeVisible({ timeout: 90_000 });
  });

  await test.step("asking a question returns an answer with its source", async () => {
    await page
      .getByRole("button", { name: /what is the refund policy\?/i })
      .click();

    // The answer is grounded in the uploaded document.
    await expect(page.getByText(/30 days/i).first()).toBeVisible({
      timeout: 60_000,
    });

    // And it shows where it came from, labelled "Sources" rather than
    // "citations".
    await expect(page.getByText(/^sources$/i)).toBeVisible();
    await expect(page.getByText(/refund-policy/i).first()).toBeVisible();
    await expect(page.getByText(/citations/i)).toHaveCount(0);
  });

  await test.step("finishing setup lands on a dashboard with real data", async () => {
    await page.getByRole("button", { name: /go to dashboard/i }).click();
    await expect(page).toHaveURL(/\/dashboard$/);

    await expect(page.getByText(/your assistant is ready/i)).toBeVisible();
    await expect(page.getByText(/^knowledge spaces$/i)).toBeVisible();
    await expect(page.getByText(/^ready for chat$/i)).toBeVisible();
  });

  await test.step("no backend vocabulary or raw identifiers reached the screen", async () => {
    const body = (await page.locator("body").innerText()).toLowerCase();
    for (const term of ["ingest", "embedding", "knowledge base", "organization_id"]) {
      expect(body, `"${term}" should never appear in the UI`).not.toContain(term);
    }

    // UUIDs are the other thing that must never surface.
    expect(body).not.toMatch(
      /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/,
    );
  });
});
