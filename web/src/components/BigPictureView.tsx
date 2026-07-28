import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getBigPictureApiBigPictureGet, type BigPicture } from "../api";
import { HygieneAlert } from "./HygieneAlert";
import { ProvenanceChip } from "./ProvenanceChip";

const pct = (v: number | null) => (v === null ? null : `${Math.round(v * 100)}%`);
const hours = (v: number | null) => (v === null ? null : `${(v / 3600).toFixed(1)}h`);

// done é o único status que "ganha" o verde de evidência (ADR-017): é provado pelo CI.
const statusClass = (status: string) =>
  status === "done" ? "text-evidence" : status === "in_progress" ? "text-primary" : "";

export function BigPictureView({ onOpenSpec }: { onOpenSpec: (specId: string) => void }) {
  const { t } = useTranslation();
  const [data, setData] = useState<BigPicture | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getBigPictureApiBigPictureGet()
      .then(setData)
      .catch(() => setError(true));
  }, []);

  if (error) return <p className="text-destructive">{t("loadError")}</p>;
  if (!data) return <p className="text-muted-foreground">{t("loading")}</p>;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
        <span>
          {t("phase")}: <strong className="text-foreground">{data.phase}</strong>
        </span>
        <span>
          {t("sprint")}: <strong className="text-foreground">{data.sprint ?? t("noData")}</strong>
        </span>
      </div>

      {data.data_source === "demo" && (
        <p className="rounded-md border border-readiness-mid bg-readiness-mid/10 px-3 py-2 text-sm">
          {t("demoBanner")}
        </p>
      )}

      <HygieneAlert hygiene={data.hygiene} />

      <section>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide">{t("specsByStatus")}</h2>
        <div className="flex flex-wrap gap-2">
          {data.specs_by_status.map((s) => (
            <span key={s.status} className="rounded-md bg-card px-3 py-1 text-sm">
              <span className={statusClass(s.status)}>{s.status}</span>{" "}
              <span className="font-mono">{s.count}</span>
              <ProvenanceChip source="registry" />
            </span>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide">{t("sprintMetrics")}</h2>
        <div className="overflow-x-auto rounded-md border border-border">
          <table className="w-full text-left text-sm">
            <thead className="bg-card text-muted-foreground">
              <tr>
                <th className="p-2">{t("spec")}</th>
                <th className="p-2">{t("status")}</th>
                <th className="p-2">{t("firstRun")}</th>
                <th className="p-2">{t("cycleTime")}</th>
                <th className="p-2">{t("turnover")}</th>
                <th className="p-2">{t("commits")}</th>
              </tr>
            </thead>
            <tbody>
              {data.metrics.map((m) => (
                <tr
                  key={m.spec_id}
                  className="cursor-pointer border-t border-border hover:bg-card"
                  onClick={() => onOpenSpec(m.spec_id)}
                >
                  <td className="p-2 font-mono">{m.spec_id}</td>
                  <td className={`p-2 ${statusClass(m.status)}`}>{m.status}</td>
                  <td className="p-2 font-mono">{pct(m.first_run_pass_rate) ?? t("noData")}</td>
                  <td className="p-2 font-mono">{hours(m.cycle_time_seconds) ?? t("noData")}</td>
                  <td className="p-2 font-mono">{m.turnover_30d?.toFixed(2) ?? t("noData")}</td>
                  <td className="p-2 font-mono">{m.commits}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          {t("sprintMetrics")}
          <ProvenanceChip source="snapshot SPEC-013" />
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide">{t("perception")}</h2>
        <div className="flex flex-wrap gap-4 text-sm">
          <span>
            {t("samples")}: <span className="font-mono">{data.perception.n_samples}</span>
          </span>
          <span>
            {t("skips")}: <span className="font-mono">{data.perception.n_skipped}</span>
          </span>
          <span>
            {t("avgUsefulness")}:{" "}
            <span className="font-mono">
              {data.perception.aproveitamento_mean?.toFixed(1) ?? t("noData")}
            </span>
          </span>
          <span>
            {t("perceptionGap")}:{" "}
            <span className="font-mono">{pct(data.perception.perception_gap) ?? t("noData")}</span>
          </span>
          <ProvenanceChip source="survey SPEC-014" />
        </div>
      </section>
    </div>
  );
}
