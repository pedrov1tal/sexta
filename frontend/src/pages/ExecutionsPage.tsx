import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Check,
  Circle,
  ClipboardCheck,
  Clock3,
  Play,
  Plus,
  RefreshCw,
  Utensils,
} from "lucide-react";
import { errorMessage, kitchenApi } from "../lib/api";
import { formatDateTime, operationDateKey } from "../lib/format";
import type { Checklist, ChecklistExecution } from "../types";
import {
  Dialog,
  EmptyState,
  ErrorBanner,
  LoadingState,
  PageHeader,
  ProgressBar,
  StatusBadge,
  SuccessMessage,
  buttonPrimary,
  buttonSecondary,
  inputClass,
} from "../components/ui";

export function ExecutionsPage() {
  const [executions, setExecutions] = useState<ChecklistExecution[]>([]);
  const [checklists, setChecklists] = useState<Checklist[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busyTaskId, setBusyTaskId] = useState<number | null>(null);
  const [startDialogOpen, setStartDialogOpen] = useState(false);
  const [selectedChecklistId, setSelectedChecklistId] = useState("");
  const [starting, setStarting] = useState(false);

  const loadData = useCallback(async (quiet = false) => {
    if (quiet) setRefreshing(true);
    else setLoading(true);
    setError("");
    try {
      const [items, executionItems] = await Promise.all([
        kitchenApi.listChecklists(),
        kitchenApi.listExecutions(0, 100),
      ]);
      setChecklists(items);
      setExecutions(executionItems);
      setSelectedChecklistId((current) => {
        if (current && items.some((item) => item.id === Number(current))) {
          return current;
        }
        return String(items.find((item) => item.is_active && item.tasks.length)?.id ?? "");
      });
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const checklistNames = useMemo(
    () => new Map(checklists.map((item) => [item.id, item.title])),
    [checklists],
  );
  const activeExecutions = useMemo(
    () => executions.filter((execution) => execution.status !== "completed"),
    [executions],
  );
  const startableChecklists = checklists.filter(
    (checklist) =>
      checklist.is_active &&
      checklist.tasks.length > 0 &&
      !executions.some(
        (execution) =>
          execution.checklist_id === checklist.id &&
          execution.execution_date === operationDateKey(),
      ),
  );

  async function handleStart() {
    const checklistId = Number(selectedChecklistId);
    if (!checklistId) return;
    setStarting(true);
    setError("");
    try {
      await kitchenApi.startExecution(checklistId);
      setStartDialogOpen(false);
      setSuccess("Execução iniciada. A equipe já pode registrar as tarefas.");
      await loadData(true);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setStarting(false);
    }
  }

  async function handleComplete(executionId: number, taskId: number) {
    setBusyTaskId(taskId);
    setError("");
    setSuccess("");
    try {
      const updated = await kitchenApi.completeTask(executionId, taskId);
      setExecutions((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      if (updated.status === "completed") {
        setSuccess("Checklist finalizado: todas as tarefas obrigatórias foram concluídas.");
      }
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setBusyTaskId(null);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Acompanhamento em tempo real"
        title="Execuções"
        description="Acompanhe as rotinas em andamento e registre cada tarefa concluída."
        action={
          <div className="flex gap-2">
            <button
              className={buttonSecondary}
              disabled={refreshing}
              onClick={() => void loadData(true)}
              type="button"
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
              <span className="hidden sm:inline">Atualizar</span>
            </button>
            <button
              className={buttonPrimary}
              disabled={!startableChecklists.length}
              onClick={() => setStartDialogOpen(true)}
              type="button"
            >
              <Plus className="h-4 w-4" />
              Iniciar execução
            </button>
          </div>
        }
      />
      {error && <ErrorBanner message={error} onDismiss={() => setError("")} />}
      {success && <SuccessMessage>{success}</SuccessMessage>}

      <section className="mb-5 grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-card">
          <p className="text-xs text-muted">Em andamento</p>
          <p className="mt-2 text-2xl font-bold text-ink">
            {activeExecutions.filter((item) => item.status === "in_progress").length}
          </p>
        </div>
        <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-card">
          <p className="text-xs text-muted">Atrasadas</p>
          <p className="mt-2 text-2xl font-bold text-rose-600">
            {activeExecutions.filter((item) => item.status === "overdue").length}
          </p>
        </div>
        <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-card">
          <p className="text-xs text-muted">Tarefas pendentes</p>
          <p className="mt-2 text-2xl font-bold text-ink">
            {activeExecutions.reduce(
              (total, execution) =>
                total +
                execution.task_executions.filter((task) => !task.is_completed).length,
              0,
            )}
          </p>
        </div>
      </section>

      {loading ? (
        <LoadingState label="Carregando execuções..." />
      ) : activeExecutions.length ? (
        <div className="space-y-4">
          {activeExecutions.map((execution) => {
            const completedCount = execution.task_executions.filter(
              (task) => task.is_completed,
            ).length;
            return (
              <article
                className="overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-card"
                key={execution.id}
              >
                <div className="border-b border-slate-100 p-5 sm:px-6">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-mint text-leaf">
                        <Utensils className="h-5 w-5" />
                      </div>
                      <div>
                        <h2 className="font-bold text-ink">
                          {checklistNames.get(execution.checklist_id) ??
                            `Checklist #${execution.checklist_id}`}
                        </h2>
                        <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
                          <span className="inline-flex items-center gap-1">
                            <Clock3 className="h-3.5 w-3.5" />
                            Iniciada {formatDateTime(execution.started_at)}
                          </span>
                          <span>Execução #{execution.id}</span>
                        </div>
                      </div>
                    </div>
                    <StatusBadge status={execution.status} />
                  </div>
                  <div className="mt-5 grid gap-3 sm:grid-cols-[1fr_auto] sm:items-center">
                    <ProgressBar value={execution.completion_percentage} />
                    <p className="text-right text-xs text-muted">
                      {completedCount} de {execution.task_executions.length} tarefas
                    </p>
                  </div>
                </div>

                <div className="divide-y divide-slate-100 px-5 sm:px-6">
                  {execution.task_executions.map((taskExecution) => (
                    <div
                      className="flex items-center gap-3 py-3.5"
                      key={taskExecution.id}
                    >
                      <button
                        aria-label={
                          taskExecution.is_completed
                            ? `${taskExecution.task.title} concluída`
                            : `Marcar ${taskExecution.task.title} como concluída`
                        }
                        className={`grid h-6 w-6 shrink-0 place-items-center rounded-full border transition ${
                          taskExecution.is_completed
                            ? "border-leaf bg-leaf text-white"
                            : "border-slate-300 text-transparent hover:border-leaf"
                        }`}
                        disabled={
                          taskExecution.is_completed ||
                          execution.status === "completed" ||
                          busyTaskId === taskExecution.task_id
                        }
                        onClick={() =>
                          void handleComplete(execution.id, taskExecution.task_id)
                        }
                        type="button"
                      >
                        {taskExecution.is_completed ? (
                          <Check className="h-3.5 w-3.5" />
                        ) : busyTaskId === taskExecution.task_id ? (
                          <span className="h-2 w-2 animate-pulse rounded-full bg-leaf" />
                        ) : (
                          <Circle className="h-3.5 w-3.5" />
                        )}
                      </button>
                      <div className="min-w-0 flex-1">
                        <p
                          className={`text-sm font-medium ${
                            taskExecution.is_completed
                              ? "text-slate-400 line-through"
                              : "text-ink"
                          }`}
                        >
                          {taskExecution.task.title}
                        </p>
                        {taskExecution.task.description && (
                          <p className="mt-0.5 truncate text-xs text-muted">
                            {taskExecution.task.description}
                          </p>
                        )}
                      </div>
                      <span
                        className={`hidden rounded-full px-2 py-1 text-[10px] font-semibold sm:inline-flex ${
                          taskExecution.task.is_required
                            ? "bg-emerald-50 text-emerald-700"
                            : "bg-slate-100 text-slate-500"
                        }`}
                      >
                        {taskExecution.task.is_required ? "Obrigatória" : "Opcional"}
                      </span>
                    </div>
                  ))}
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <section className="rounded-2xl border border-slate-100 bg-white shadow-card">
          <EmptyState
            action={
              startableChecklists.length ? (
                <button
                  className={buttonPrimary}
                  onClick={() => setStartDialogOpen(true)}
                  type="button"
                >
                  <Play className="h-4 w-4" />
                  Iniciar primeira execução
                </button>
              ) : undefined
            }
            description={
              startableChecklists.length
                ? "Inicie uma rotina para acompanhar as tarefas da equipe."
                : "Cadastre um checklist ativo com tarefas para iniciar uma execução."
            }
            icon={<ClipboardCheck className="h-5 w-5" />}
            title="Nenhuma execução em andamento"
          />
        </section>
      )}

      {startDialogOpen && (
        <Dialog
          description="Escolha uma rotina ativa com tarefas cadastradas."
          onClose={() => setStartDialogOpen(false)}
          title="Iniciar execução"
        >
          <div className="space-y-5">
            {startableChecklists.length ? (
              <label className="block">
                <span className="form-label">Checklist</span>
                <select
                  className={inputClass}
                  onChange={(event) => setSelectedChecklistId(event.target.value)}
                  value={selectedChecklistId}
                >
                  {startableChecklists.map((checklist) => (
                    <option key={checklist.id} value={checklist.id}>
                      {checklist.title}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <p className="rounded-xl bg-amber-50 p-4 text-sm text-amber-800">
                Não há checklists elegíveis para iniciar agora. A API permite
                apenas uma execução por checklist em cada data operacional.
              </p>
            )}
            <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
              <button
                className={buttonSecondary}
                onClick={() => setStartDialogOpen(false)}
                type="button"
              >
                Cancelar
              </button>
              <button
                className={buttonPrimary}
                disabled={!startableChecklists.length || starting}
                onClick={() => void handleStart()}
                type="button"
              >
                {starting ? "Iniciando..." : "Confirmar início"}
              </button>
            </div>
          </div>
        </Dialog>
      )}
    </>
  );
}
