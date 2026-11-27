import { getTranslations } from "next-intl/server";

import { buttonVariants } from "@/components/ui/button";
import { Link } from "@/i18n/navigation";

export default async function NotFoundPage() {
  const t = await getTranslations("notFound");

  return (
    <main
      id="main-content"
      className="mx-auto flex w-full max-w-xl flex-1 flex-col justify-center gap-4 px-4 py-16"
    >
      <h1 className="text-2xl font-semibold">{t("title")}</h1>
      <p className="text-muted-foreground">{t("description")}</p>
      <Link href="/" className={buttonVariants({ variant: "outline", className: "self-start" })}>
        {t("backHome")}
      </Link>
    </main>
  );
}
