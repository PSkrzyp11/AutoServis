import { getTranslations } from "next-intl/server";
import { type ReactNode, Suspense } from "react";

import { AppHeader } from "@/components/app-header";
import { AuthGuard } from "@/features/auth/components/auth-guard";

async function LoadingState() {
  const t = await getTranslations("common");
  return (
    <p role="status" className="p-6 text-sm text-muted-foreground">
      {t("loading")}
    </p>
  );
}

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<LoadingState />}>
      <AuthGuard>
        <AppHeader />
        <main id="main-content" className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
          {children}
        </main>
      </AuthGuard>
    </Suspense>
  );
}
