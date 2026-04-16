import { expect, test } from "@playwright/test";

test.describe("health + chat mock E2E", () => {
  test("/health returns ok", async ({ request }) => {
    const res = await request.get("http://127.0.0.1:8000/health");
    expect(res.ok()).toBeTruthy();
    const body = (await res.json()) as { status?: string };
    expect(body.status).toBe("ok");
  });

  test("chat page renders mock POST /api/v1/chat response", async ({ page }) => {
    await page.route("**/api/v1/chat", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          answer: "mock answer visible",
          sources: [],
          chunks: [],
          tool_name: "rag_search",
          extra: null,
          latency_sec: 0.01,
          next_original_question_for_clarification: null,
          next_chart_confirmation_question: null,
        }),
      });
    });

    await page.goto("/chat");
    await page.getByRole("button", { name: "Legal Assistant" }).click();
    await page.getByTestId("chat-input").fill("hello");
    await page.getByTestId("chat-send").click();
    await expect(page.getByText("mock answer visible")).toBeVisible();
  });
});
