import { createTranslator } from "next-intl";
import { describe, expect, it } from "vitest";

import { createRegisterSchema } from "@/features/auth/schemas";

import messages from "../../../messages/pl.json";

const t = createTranslator({ locale: "pl", messages, namespace: "validation" });

const validRegistration = {
  fullName: "Anna Nowak",
  email: "anna.nowak@example.com",
  phone: "+48 600 100 200",
  password: "Bezpieczne-haslo-1",
  confirmPassword: "Bezpieczne-haslo-1",
};

function issueMessages(input: typeof validRegistration): Record<string, string> {
  const result = createRegisterSchema(t).safeParse(input);
  if (result.success) {
    return {};
  }
  return Object.fromEntries(
    result.error.issues.map((issue) => [issue.path.join("."), issue.message]),
  );
}

describe("createRegisterSchema", () => {
  it("accepts a valid registration with optional empty phone", () => {
    expect(issueMessages({ ...validRegistration, phone: "" })).toEqual({});
  });

  it("uses Polish plural forms in length messages", () => {
    const issues = issueMessages({
      ...validRegistration,
      fullName: "A",
      password: "krotkie",
      confirmPassword: "krotkie",
    });

    expect(issues.fullName).toBe("Imię i nazwisko musi mieć co najmniej 2 znaki.");
    expect(issues.password).toBe("Hasło musi mieć co najmniej 8 znaków.");
  });

  it("reports mismatched passwords on the confirmation field", () => {
    const issues = issueMessages({ ...validRegistration, confirmPassword: "Inne-haslo-123" });

    expect(issues.confirmPassword).toBe("Hasła nie są takie same.");
  });

  it("rejects an invalid email and phone number", () => {
    const issues = issueMessages({ ...validRegistration, email: "anna", phone: "123" });

    expect(issues.email).toBe("Podaj poprawny adres e-mail.");
    expect(issues.phone).toBe("Podaj poprawny numer telefonu, np. +48 600 100 200.");
  });
});
