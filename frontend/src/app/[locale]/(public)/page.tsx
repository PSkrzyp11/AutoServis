import { SearchIcon } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { buttonVariants } from "@/components/ui/button";
import { Link } from "@/i18n/navigation";

export default async function HomePage() {
  const t = await getTranslations("home");

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center gap-6 px-4 py-16">
      <h1 className="text-3xl font-semibold tracking-tight text-balance sm:text-5xl">
        {t("title")}
      </h1>
      <p className="text-lg text-muted-foreground">{t("description")}</p>
      <div className="flex flex-wrap gap-3">
        <Link href="/workshops" className={buttonVariants({ size: "lg" })}>
          <SearchIcon aria-hidden="true" />
          {t("findWorkshop")}
        </Link>
        <Link href="/register" className={buttonVariants({ size: "lg", variant: "outline" })}>
          {t("register")}
        </Link>
      </div>
    </div>
  );
}
