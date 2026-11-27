import { useTranslations } from "next-intl";
import { useCallback } from "react";

import { splitDuration } from "@/lib/duration";

export function useFormatDuration(): (totalMinutes: number) => string {
  const t = useTranslations("common");
  return useCallback(
    (totalMinutes: number) => {
      const { hours, minutes } = splitDuration(totalMinutes);
      return hours === 0
        ? t("durationMinutes", { minutes })
        : t("durationHours", { hours, minutes });
    },
    [t],
  );
}
