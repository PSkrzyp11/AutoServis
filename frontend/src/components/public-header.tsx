"use client";

import { WrenchIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useSyncExternalStore } from "react";

import { buttonVariants } from "@/components/ui/button";
import { Link } from "@/i18n/navigation";
import { SESSION_HINT_COOKIE } from "@/lib/session";

function subscribeToNothing(): () => void {
  return () => undefined;
}

function readSessionHint(): boolean {
  return document.cookie.split("; ").some((entry) => entry.startsWith(`${SESSION_HINT_COOKIE}=`));
}

function readServerSessionHint(): boolean {
  return false;
}

export function PublicHeader() {
  const t = useTranslations("navigation");
  const tCommon = useTranslations("common");
  const hasSession = useSyncExternalStore(
    subscribeToNothing,
    readSessionHint,
    readServerSessionHint,
  );

  return (
    <header className="border-b">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-2 px-4 py-3">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <WrenchIcon aria-hidden="true" className="size-5" />
          {tCommon("appName")}
        </Link>
        <nav aria-label={t("label")} className="flex flex-wrap items-center gap-1">
          <Link href="/workshops" className={buttonVariants({ variant: "ghost" })}>
            {t("findWorkshop")}
          </Link>
          {hasSession ? (
            <Link href="/account" className={buttonVariants({ variant: "secondary" })}>
              {t("account")}
            </Link>
          ) : (
            <>
              <Link href="/login" className={buttonVariants({ variant: "ghost" })}>
                {t("login")}
              </Link>
              <Link href="/register" className={buttonVariants({ variant: "secondary" })}>
                {t("register")}
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
