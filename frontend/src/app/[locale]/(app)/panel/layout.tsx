import type { ReactNode } from "react";

import { AuthGuard } from "@/features/auth/components/auth-guard";
import { PanelShell } from "@/features/workshop-panel/components/panel-shell";
import { STAFF_ROLES } from "@/lib/api/types";

export default function PanelLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard allowedRoles={STAFF_ROLES}>
      <PanelShell>{children}</PanelShell>
    </AuthGuard>
  );
}
