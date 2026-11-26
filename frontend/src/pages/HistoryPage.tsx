import { useCallback, useEffect, useMemo, useState } from "react";
import { Clock3, History as HistoryIcon, Search } from "lucide-react";
import { errorMessage, kitchenApi } from "../lib/api";
import {
  executionStatusLabels,
  formatDate,
} from "../lib/format";
import type { Checklist, ChecklistExecution, ExecutionStatus } from "../types";
import {
  EmptyState,
  ErrorBanner,
  LoadingState,
  PageHeader,
  ProgressBar,
  StatusBadge,
  buttonSecondary,
  inputClass,
} from "../components/ui";

const pageSize = 25;

export function HistoryPage() {
  const [executions, setExecutions] = useState<ChecklistExecution[]>([]);
  const [checklists, setChecklists] = useState<Checklist[]>([]);
  const [page, setPage] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [statusFilter, setStatusFilter] = useState<ExecutionStatus | "all">("all");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadPage = useCallback(async (pageIndex: number) => {
    setLoading(true);
    setError("");
    try {
      const [items, checklistItems] = await Promise.all([
        kitchenApi.listExecutions(pageIndex * pageSize, pageSize),
        kitchenApi.listChecklists(),
      ]);
      setExecutions(items);
      setChecklists(checklistItems);
      setHasNext(items.length === pageSize);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadPage(page);
  }, [loadPage, page]);

  const checklistNames = useMemo(
    () => new Map(checklists.map((item) => [item.id, item.title])),
    [checklists],
  );
  const filtered = executions.filter((execution) => {
    const matchesStatus =
      statusFilter === "all" || execution.status === statusFilter;
    const name =
      checklistNames.get(execution.checklist_id) ??
      `Checklist #${execution.checklist_id}`;
    const matchesQuery =
      !query.trim() ||
      `${name} ${execution.execution_date} ${execution.id}`
        .toLowerCase()
        .includes(query.trim().toLowerCase());
    return matchesStatus && matchesQuery;
  });

  return (
    <>
      <PageHeader
        eyebrow="Registro operacional"
        title="Histórico"
        description="Consulte as execuções anteriores, seus resultados e tarefas concluídas."
      />
      {error && <ErrorBanner message={error} onDismiss={() => setError("")} />}

      <section className="rounded-2xl border border-slate-100 bg-white p-4 shadow-card sm:p-5">
        <div className="mb-5 flex flex-wrap gap-3">
          <div className="relative min-w-[210px] flex-1 sm:max-w-sm">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              className={`${inputClass} pl-9`}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Buscar checklist ou data..."
              value={query}
            />
          </div>
          <select
            className={`${inputClass} sm:w-48`}
            onChange={(event) =>
              setStatusFilter(event.target.value as ExecutionStatus | "all")
            }
            value={statusFilter}
          >
            <option value="all">Todos os status</option>
            {Object.entries(executionStatusLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        {loading ? (
          <LoadingState label="Carregando histórico..." />
        ) : filtered.length ? (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] border-collapse text-left">
                <thead>
                  <tr className="border-b border-slate-100 text-[10px] font-bold uppercase tracking-[.12em] text-slate-400">
                    <th className="px-3 py-3">Checklist</th>
                    <th className="px-3 py-3">Data operacional</th>
                    <th className="px-3 py-3">Status</th>
                    <th className="px-3 py-3">Conclusão</th>
                    <th className="px-3 py-3">Tarefas</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filtered.map((execution) => {
                    const complete = execution.task_executions.filter(
                      (task) => task.is_completed,
                    ).length;
                    return (
                      <tr className="text-sm" key={execution.id}>
                        <td className="px-3 py-4">
                          <p className="font-semibold text-ink">
                            {checklistNames.get(execution.checklist_id) ??
                              `Checklist #${execution.checklist_id}`}
                          </p>
                          <p className="mt-1 text-[11px] text-muted">
                            Execução #{execution.id}
                          </p>
                        </td>
                        <td className="px-3 py-4 text-slate-600">
                          {formatDate(execution.execution_date)}
                        </td>
                        <td className="px-3 py-4">
                          <StatusBadge status={execution.status} />
                        </td>
                        <td className="w-48 px-3 py-4">
                          <ProgressBar value={execution.completion_percentage} />
                        </td>
                        <td className="px-3 py-4 text-xs text-slate-600">
                          {complete}/{execution.task_executions.length} concluídas
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-4">
              <p className="text-xs text-muted">
                Página {page + 1} · {executions.length} registros nesta página
              </p>
              <div className="flex gap-2">
                <button
                  className={buttonSecondary}
                  disabled={page === 0 || loading}
                  onClick={() => setPage((current) => Math.max(0, current - 1))}
                  type="button"
                >
                  Anterior
                </button>
                <button
                  className={buttonSecondary}
                  disabled={!hasNext || loading}
                  onClick={() => setPage((current) => current + 1)}
                  type="button"
                >
                  Próxima
                </button>
              </div>
            </div>
          </>
        ) : (
          <EmptyState
            description={
              query || statusFilter !== "all"
                ? "Altere os filtros para encontrar outras execuções."
                : "As execuções iniciadas serão registradas automaticamente neste histórico."
            }
            icon={<HistoryIcon className="h-5 w-5" />}
            title={
              query || statusFilter !== "all"
                ? "Nenhuma execução encontrada"
                : "Histórico vazio"
            }
          />
        )}
      </section>
      <div className="mt-4 flex items-center gap-2 text-[11px] text-muted">
        <Clock3 className="h-3.5 w-3.5" />
        O histórico é fornecido pela API e pode ser consultado em páginas de 25
        registros.
      </div>
    </>
  );
}
