// ADR-017: todo número em tela carrega um chip de proveniência. Número sem
// origem não entra. Aqui a origem é o artefato bruto de onde o dado veio.
export function ProvenanceChip({ source }: { source: string }) {
  return (
    <span
      className="ml-1 rounded-sm bg-secondary px-1 py-0.5 align-middle font-mono text-[10px] text-provenance"
      title={`Proveniência: ${source}`}
    >
      via {source}
    </span>
  );
}
