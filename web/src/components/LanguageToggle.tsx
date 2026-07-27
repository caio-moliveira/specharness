import { useTranslation } from "react-i18next";

// Troca de idioma (acceptance[4]): inglês base, pt-BR selecionável.
export function LanguageToggle() {
  const { i18n, t } = useTranslation();
  const languages: Array<{ code: string; label: string }> = [
    { code: "en", label: "EN" },
    { code: "pt-BR", label: "PT-BR" },
  ];
  return (
    <div className="flex items-center gap-1 text-xs" aria-label={t("language")}>
      {languages.map((lang) => (
        <button
          key={lang.code}
          onClick={() => void i18n.changeLanguage(lang.code)}
          aria-pressed={i18n.language === lang.code}
          className={`rounded-sm px-2 py-1 ${
            i18n.language === lang.code
              ? "bg-primary text-primary-foreground"
              : "bg-secondary text-secondary-foreground"
          }`}
        >
          {lang.label}
        </button>
      ))}
    </div>
  );
}
