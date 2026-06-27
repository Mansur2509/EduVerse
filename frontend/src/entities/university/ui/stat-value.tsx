"use client";

import { useI18n } from "@/shared/i18n";

export function StatValue({
  value,
  suffix
}: {
  value: string | number | boolean | null;
  suffix?: string;
}) {
  const { t } = useI18n();
  if (value === null || value === undefined || value === "") {
    return (
      <span className="italic text-muted-foreground">{t("universities.notVerifiedYet")}</span>
    );
  }
  if (typeof value === "boolean") {
    return <span>{value ? t("common.yes") : t("common.no")}</span>;
  }
  return (
    <span>
      {value}
      {suffix ?? ""}
    </span>
  );
}
