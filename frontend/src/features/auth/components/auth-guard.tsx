"use client";

import { useRouter as useNextRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { type ReactNode, useEffect } from "react";

import { StatusMessage } from "@/components/status-message";
import { useCurrentUser } from "@/features/auth/api";
import { useApiErrorMessage } from "@/hooks/use-api-error-message";
import { usePathname } from "@/i18n/navigation";
import { localizePathname, routing } from "@/i18n/routing";
import { isApiErrorWithStatus } from "@/lib/api/errors";
import type { UserRole } from "@/lib/api/types";
import { REDIRECT_QUERY_PARAM } from "@/lib/session";

const SESSION_ERROR_STATUSES = [401, 403];

type AuthGuardProps = {
  children: ReactNode;
  requiredRole?: UserRole;
};

function buildLoginUrl(returnPath: string): string {
  const loginPath = localizePathname("/login", routing.defaultLocale);
  const query = new URLSearchParams({ [REDIRECT_QUERY_PARAM]: returnPath });
  return `${loginPath}?${query.toString()}`;
}

export function AuthGuard({ children, requiredRole }: AuthGuardProps) {
  const t = useTranslations();
  const errorMessage = useApiErrorMessage();
  const nextRouter = useNextRouter();
  const pathname = usePathname();
  const currentUser = useCurrentUser();
  const isSessionMissing = isApiErrorWithStatus(currentUser.error, ...SESSION_ERROR_STATUSES);

  useEffect(() => {
    if (isSessionMissing) {
      nextRouter.replace(buildLoginUrl(window.location.pathname));
    }
  }, [isSessionMissing, nextRouter, pathname]);

  if (currentUser.isPending || isSessionMissing) {
    return (
      <p role="status" className="p-6 text-sm text-muted-foreground">
        {t("common.loading")}
      </p>
    );
  }

  if (currentUser.isError) {
    return <StatusMessage tone="error" message={errorMessage(currentUser.error)} />;
  }

  if (requiredRole && currentUser.data.role !== requiredRole) {
    return <StatusMessage tone="error" message={t("errors.FORBIDDEN")} />;
  }

  return children;
}
