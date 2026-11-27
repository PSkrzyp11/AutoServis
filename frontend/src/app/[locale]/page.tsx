import { WrenchIcon } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { buttonVariants } from "@/components/ui/button";
import { Link } from "@/i18n/navigation";

export default async function HomePage() {
  const t = await getTranslations();

  return (
    <main
      id="main-content"
      className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center gap-6 px-4 py-16"
    >
      <p className="flex items-center gap-2 font-semibold">
        <WrenchIcon aria-hidden="true" className="size-5" />
        {t("common.appName")}
      </p>
      <h1 className="text-3xl font-semibold tracking-tight text-balance sm:text-5xl">
        {t("home.title")}
      </h1>
      <p className="text-lg text-muted-foreground">{t("home.description")}</p>
      <div className="flex flex-wrap gap-3">
        <Link href="/login" className={buttonVariants({ size: "lg" })}>
          {t("home.login")}
        </Link>
        <Link href="/register" className={buttonVariants({ size: "lg", variant: "outline" })}>
          {t("home.register")}
        </Link>
      </div>
    </main>
  );
}
