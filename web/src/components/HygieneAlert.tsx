import { useTranslation } from "react-i18next";
import type { Hygiene } from "../api";
import { ProvenanceChip } from "./ProvenanceChip";

// Alerta de higiene na big picture: aparece quando há commits órfãos (> 0), com a
// contagem e um link para a lista (acceptance / cenário de higiene).
export function HygieneAlert({ hygiene }: { hygiene: Hygiene }) {
  const { t } = useTranslation();
  if (hygiene.orphan_commits === 0) return null;
  return (
    <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm">
      <strong className="text-destructive">⚠ {t("hygiene")}:</strong>{" "}
      <span className="font-mono">{hygiene.orphan_commits}</span> {t("orphanCommits")}
      <ProvenanceChip source="git" /> ·{" "}
      <span className="font-mono">{hygiene.orphan_specs}</span> {t("orphanSpecs")}{" "}
      <a href="#orphans" className="underline">
        {t("viewList")}
      </a>
    </div>
  );
}
