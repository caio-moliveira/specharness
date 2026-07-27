import { useState } from "react";
import { useTranslation } from "react-i18next";
import { BigPictureView } from "./components/BigPictureView";
import { LanguageToggle } from "./components/LanguageToggle";
import { PipelineView } from "./components/PipelineView";

// Read-only na Fase A: alterna entre a big picture e a pipeline de uma spec.
// Wizards chegam na Fase B (SPEC-001 §5).
export default function App() {
  const { t } = useTranslation();
  const [openSpec, setOpenSpec] = useState<string | null>(null);

  return (
    <div className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 p-6">
      <header className="flex items-center justify-between border-b border-border pb-4">
        <h1 className="text-xl font-semibold">{t("title")}</h1>
        <LanguageToggle />
      </header>
      <main>
        {openSpec === null ? (
          <BigPictureView onOpenSpec={setOpenSpec} />
        ) : (
          <PipelineView specId={openSpec} onBack={() => setOpenSpec(null)} />
        )}
      </main>
    </div>
  );
}
