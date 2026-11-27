import type { ReactNode } from "react";

import { AppHeader } from "@/components/app-header";
import { AuthGuard } from "@/features/auth/components/auth-guard";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      <AppHeader />
      <main id="main-content" className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
        {children}
      </main>
    </AuthGuard>
  );
}
