import { describe, expect, it } from "vitest";

import { localizePathname } from "@/i18n/routing";
import { resolveSafeRedirect } from "@/lib/session";

describe("resolveSafeRedirect", () => {
  it.each(["/konto", "/admin/uzytkownicy?page=2"])("accepts local path %s", (path) => {
    expect(resolveSafeRedirect(path)).toBe(path);
  });

  it.each([null, "", "https://example.com", "//example.com", "/\\example.com", "konto"])(
    "rejects unsafe value %s",
    (value) => {
      expect(resolveSafeRedirect(value)).toBeNull();
    },
  );
});

describe("localizePathname", () => {
  it("returns Polish paths without a locale prefix for the default locale", () => {
    expect(localizePathname("/login", "pl")).toBe("/logowanie");
    expect(localizePathname("/admin/users", "pl")).toBe("/admin/uzytkownicy");
    expect(localizePathname("/", "pl")).toBe("/");
  });
});
