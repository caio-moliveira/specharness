import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getSpecPipelineApiSpecsSpecIdPipelineGet, type SpecPipeline } from "../api";

// A visão pipeline conta a história da spec em ordem: readiness → commits → BDD
// → review → percepção (acceptance / cenário 2). Verde só em estágio "done".
const dotClass = (status: string) =>
  status === "done"
    ? "bg-evidence"
    : status === "unavailable"
      ? "bg-provenance"
      : "bg-readiness-mid";

const stageKey: Record<string, string> = {
  readiness: "stageReadiness",
  commits: "stageCommits",
  bdd: "stageBdd",
  review: "stageReview",
  perception: "stagePerception",
};

export function PipelineView({ specId, onBack }: { specId: string; onBack: () => void }) {
  const { t } = useTranslation();
  const [data, setData] = useState<SpecPipeline | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setData(null);
    setError(false);
    getSpecPipelineApiSpecsSpecIdPipelineGet({ specId })
      .then(setData)
      .catch(() => setError(true));
  }, [specId]);

  return (
    <div className="flex flex-col gap-4">
      <button onClick={onBack} className="self-start text-sm text-primary underline">
        {t("backToBigPicture")}
      </button>
      <h2 className="font-mono text-lg">
        {t("pipeline")}: {specId}
      </h2>
      {error && <p className="text-destructive">{t("loadError")}</p>}
      {!error && !data && <p className="text-muted-foreground">{t("loading")}</p>}
      {data && (
        <ol className="flex flex-col gap-3">
          {data.stages.map((stage) => (
            <li key={stage.stage} className="flex items-start gap-3">
              <span className={`mt-1.5 h-3 w-3 shrink-0 rounded-full ${dotClass(stage.status)}`} />
              <div>
                <div className="font-semibold">{t(stageKey[stage.stage] ?? stage.stage)}</div>
                <div className="text-sm text-muted-foreground">
                  {stage.detail_key
                    ? t(stage.detail_key, {
                        count: stage.detail_count ?? undefined,
                        value: stage.detail_value ?? undefined,
                        defaultValue: stage.detail,
                      })
                    : stage.detail}
                </div>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
