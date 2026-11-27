import { useTranslations } from "next-intl";
import { useCallback } from "react";

import { ApiError } from "@/lib/api/errors";

export function useApiErrorMessage(): (error: unknown) => string {
  const t = useTranslations("errors");
  return useCallback(
    (error: unknown) => t(error instanceof ApiError ? error.code : "UNKNOWN_ERROR"),
    [t],
  );
}
