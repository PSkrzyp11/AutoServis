"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";

type ConfirmButtonProps = {
  label: string;
  question: string;
  onConfirm: () => void;
  disabled?: boolean;
  accessibleLabel?: string;
  confirmLabel?: string;
  dismissLabel?: string;
};

export function ConfirmButton({
  label,
  question,
  onConfirm,
  disabled,
  accessibleLabel,
  confirmLabel,
  dismissLabel,
}: ConfirmButtonProps) {
  const t = useTranslations("common");
  const [isConfirming, setIsConfirming] = useState(false);

  if (!isConfirming) {
    return (
      <Button
        variant="outline"
        size="sm"
        disabled={disabled}
        aria-label={accessibleLabel}
        onClick={() => setIsConfirming(true)}
      >
        {label}
      </Button>
    );
  }

  return (
    <div role="group" aria-label={question} className="flex flex-wrap items-center gap-2">
      <span className="text-sm">{question}</span>
      <Button
        variant="destructive"
        size="sm"
        disabled={disabled}
        onClick={() => {
          setIsConfirming(false);
          onConfirm();
        }}
      >
        {confirmLabel ?? t("confirmDelete")}
      </Button>
      <Button variant="ghost" size="sm" onClick={() => setIsConfirming(false)}>
        {dismissLabel ?? t("cancel")}
      </Button>
    </div>
  );
}
