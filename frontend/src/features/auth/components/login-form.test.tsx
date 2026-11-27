import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAuthStore } from "@/features/auth/auth-store";
import { LoginForm } from "@/features/auth/components/login-form";
import { jsonResponse, renderWithProviders } from "@/test/render-with-providers";

const localizedRouter = vi.hoisted(() => ({ replace: vi.fn(), push: vi.fn() }));
const nextRouter = vi.hoisted(() => ({ replace: vi.fn(), push: vi.fn() }));
const searchParams = vi.hoisted(() => ({ current: new URLSearchParams() }));

vi.mock("@/i18n/navigation", () => ({
  Link: ({
    href,
    children,
    className,
  }: {
    href: string;
    children: ReactNode;
    className?: string;
  }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
  useRouter: () => localizedRouter,
  usePathname: () => "/login",
}));

vi.mock("next/navigation", () => ({
  useRouter: () => nextRouter,
  useSearchParams: () => searchParams.current,
}));

const fetchMock = vi.fn<typeof fetch>();

async function fillAndSubmit(email: string, password: string) {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Adres e-mail"), email);
  await user.type(screen.getByLabelText("Hasło"), password);
  await user.click(screen.getByRole("button", { name: "Zaloguj się" }));
}

describe("LoginForm", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    searchParams.current = new URLSearchParams();
    useAuthStore.getState().clearAccessToken();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("shows Polish validation messages for empty fields", async () => {
    renderWithProviders(<LoginForm />);

    await userEvent.setup().click(screen.getByRole("button", { name: "Zaloguj się" }));

    expect(await screen.findAllByText("To pole jest wymagane.")).toHaveLength(2);
    expect(screen.getByLabelText("Adres e-mail")).toHaveAttribute("aria-invalid", "true");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("maps the INVALID_CREDENTIALS error code to a Polish message", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        {
          error: { code: "INVALID_CREDENTIALS", message: "Invalid email or password", details: {} },
        },
        401,
      ),
    );
    renderWithProviders(<LoginForm />);

    await fillAndSubmit("jan.kowalski@example.com", "zle-haslo");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Nieprawidłowy adres e-mail lub hasło.",
    );
  });

  it("stores the access token and opens the account page after signing in", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ access_token: "access-token", token_type: "bearer", expires_in: 900 }, 200),
    );
    renderWithProviders(<LoginForm />);

    await fillAndSubmit("jan.kowalski@example.com", "Sekretne-haslo-123");

    await vi.waitFor(() => expect(localizedRouter.replace).toHaveBeenCalledWith("/account"));
    expect(useAuthStore.getState().accessToken).toBe("access-token");
  });

  it("returns to the originally requested page when it is a safe local path", async () => {
    searchParams.current = new URLSearchParams({ next: "/admin/uzytkownicy" });
    fetchMock.mockResolvedValue(
      jsonResponse({ access_token: "access-token", token_type: "bearer", expires_in: 900 }, 200),
    );
    renderWithProviders(<LoginForm />);

    await fillAndSubmit("jan.kowalski@example.com", "Sekretne-haslo-123");

    await vi.waitFor(() => expect(nextRouter.replace).toHaveBeenCalledWith("/admin/uzytkownicy"));
    expect(localizedRouter.replace).not.toHaveBeenCalled();
  });
});
