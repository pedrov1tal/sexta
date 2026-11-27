import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  Edit3,
  ListChecks,
  Plus,
  Trash2,
} from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { errorMessage, kitchenApi } from "../lib/api";
import { checklistTypeLabels } from "../lib/format";
import type { Checklist, Task, TaskPayload } from "../types";
import {
  Dialog,
  EmptyState,
  ErrorBanner,
  LoadingState,
  PageHeader,
  buttonPrimary,
  buttonSecondary,
  inputClass,
  SuccessMessage,
} from "../components/ui";

type TaskDraft = {
  title: string;
  description: string;
  is_required: boolean;
  position: string;
};

const emptyDraft: TaskDraft = {
  title: "",
  description: "",
  is_required: true,
  position: "0",
};

export function TasksPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [checklists, setChecklists] = useState<Checklist[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loadingChecklists, setLoadingChecklists] = useState(true);
  const [loadingTasks, setLoadingTasks] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Task | null>(null);
  const [draft, setDraft] = useState<TaskDraft>(emptyDraft);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    kitchenApi
      .listChecklists()
      .then((items) => {
        if (!active) return;
        setChecklists(items);
        const requestedId = Number(searchParams.get("checklist_id"));
        const initial = items.some((item) => item.id === requestedId)
          ? requestedId
          : items[0]?.id ?? null;
        setSelectedId(initial);
      })
      .catch((requestError: unknown) => {
        if (active) setError(errorMessage(requestError));
      })
      .finally(() => {
        if (active) setLoadingChecklists(false);
      });
    return () => {
      active = false;
    };
  }, [searchParams]);

  const selectedChecklist = useMemo(
    () => checklists.find((item) => item.id === selectedId) ?? null,
    [checklists, selectedId],
  );

  const loadTasks = useCallback(async () => {
    if (selectedId === null) {
      setTasks([]);
      return;
    }
    setLoadingTasks(true);
    setError("");
    try {
      setTasks(await kitchenApi.listTasks(selectedId));
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoadingTasks(false);
    }
  }, [selectedId]);

  useEffect(() => {
    void loadTasks();
  }, [loadTasks]);

  function selectChecklist(value: string) {
    const id = Number(value);
    setSelectedId(Number.isFinite(id) ? id : null);
    setSearchParams(id ? { checklist_id: String(id) } : {});
    setSuccess("");
  }

  function openCreate() {
    setEditing(null);
    setDraft({
      ...emptyDraft,
      position: String(
        tasks.length ? Math.max(...tasks.map((task) => task.position)) + 1 : 0,
      ),
    });
    setError("");
    setDialogOpen(true);
  }

  function openEdit(task: Task) {
    setEditing(task);
    setDraft({
      title: task.title,
      description: task.description ?? "",
      is_required: task.is_required,
      position: String(task.position),
    });
    setError("");
    setDialogOpen(true);
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedId === null) return;
    setSaving(true);
    setError("");
    const payload: TaskPayload = {
      title: draft.title.trim(),
      description: draft.description.trim() || null,
      is_required: draft.is_required,
      position: Number(draft.position),
    };
    try {
      if (editing) await kitchenApi.updateTask(editing.id, payload);
      else await kitchenApi.createTask(selectedId, payload);
      setDialogOpen(false);
      setSuccess(editing ? "Tarefa atualizada." : "Tarefa adicionada ao checklist.");
      await loadTasks();
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(task: Task) {
    if (!window.confirm(`Excluir a tarefa "${task.title}"?`)) return;
    setError("");
    setSuccess("");
    try {
      await kitchenApi.deleteTask(task.id);
      setSuccess("Tarefa excluída.");
      await loadTasks();
    } catch (requestError) {
      setError(errorMessage(requestError));
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Montagem das rotinas"
        title="Tarefas"
        description="Defina o que a equipe precisa verificar e quais etapas são obrigatórias."
        action={
          <button
            className={buttonPrimary}
            disabled={!selectedChecklist}
            onClick={openCreate}
            type="button"
          >
            <Plus className="h-4 w-4" />
            Adicionar tarefa
          </button>
        }
      />
      {error && <ErrorBanner message={error} onDismiss={() => setError("")} />}
      {success && <SuccessMessage>{success}</SuccessMessage>}

      {loadingChecklists ? (
        <LoadingState label="Carregando checklists..." />
      ) : checklists.length === 0 ? (
        <section className="rounded-2xl border border-slate-100 bg-white shadow-card">
          <EmptyState
            description="Crie um checklist antes de adicionar tarefas à operação."
            icon={<ClipboardList className="h-5 w-5" />}
            title="Nenhum checklist cadastrado"
          />
        </section>
      ) : (
        <>
          <section className="mb-5 flex flex-wrap items-center gap-4 rounded-2xl border border-slate-100 bg-white p-4 shadow-card sm:p-5">
            <div className="grid h-11 w-11 place-items-center rounded-xl bg-mint text-leaf">
              <ClipboardList className="h-5 w-5" />
            </div>
            <label className="min-w-[220px] flex-1">
              <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-muted">
                Checklist selecionado
              </span>
              <select
                className={inputClass}
                onChange={(event) => selectChecklist(event.target.value)}
                value={selectedId ?? ""}
              >
                {checklists.map((checklist) => (
                  <option key={checklist.id} value={checklist.id}>
                    {checklist.title} · {checklistTypeLabels[checklist.checklist_type]}
                  </option>
                ))}
              </select>
            </label>
            {selectedChecklist && (
              <div className="text-right">
                <p className="text-xl font-bold text-ink">{tasks.length}</p>
                <p className="text-[11px] text-muted">tarefas cadastradas</p>
              </div>
            )}
          </section>

          <section className="rounded-2xl border border-slate-100 bg-white p-4 shadow-card sm:p-5">
            <div className="mb-4 flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h2 className="font-bold text-ink">
                  {selectedChecklist?.title ?? "Tarefas do checklist"}
                </h2>
                <p className="mt-1 text-xs text-muted">
                  A ordem numérica define a sequência de execução.
                </p>
              </div>
            </div>
            {loadingTasks ? (
              <LoadingState label="Carregando tarefas..." />
            ) : tasks.length ? (
              <div className="space-y-2">
                {tasks.map((task) => (
                  <article
                    className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-100 px-3 py-3 transition hover:bg-slate-50/70 sm:px-4"
                    key={task.id}
                  >
                    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-slate-100 text-xs font-bold text-slate-600">
                      {task.position + 1}
                    </span>
                    <div className="min-w-[160px] flex-1">
                      <p className="text-sm font-semibold text-ink">{task.title}</p>
                      <p className="mt-0.5 text-xs text-muted">
                        {task.description || "Sem descrição adicional"}
                      </p>
                    </div>
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-semibold ${
                        task.is_required
                          ? "bg-emerald-50 text-emerald-700"
                          : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {task.is_required ? (
                        <CheckCircle2 className="h-3.5 w-3.5" />
                      ) : (
                        <AlertTriangle className="h-3.5 w-3.5" />
                      )}
                      {task.is_required ? "Obrigatória" : "Opcional"}
                    </span>
                    <div className="ml-auto flex items-center gap-1">
                      <button
                        aria-label={`Editar ${task.title}`}
                        className="rounded-lg p-2 text-muted hover:bg-blue-50 hover:text-blue-700"
                        onClick={() => openEdit(task)}
                        type="button"
                      >
                        <Edit3 className="h-4 w-4" />
                      </button>
                      <button
                        aria-label={`Excluir ${task.title}`}
                        className="rounded-lg p-2 text-muted hover:bg-rose-50 hover:text-rose-700"
                        onClick={() => void handleDelete(task)}
                        type="button"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState
                action={
                  <button
                    className={buttonPrimary}
                    onClick={openCreate}
                    type="button"
                  >
                    <Plus className="h-4 w-4" />
                    Adicionar primeira tarefa
                  </button>
                }
                description="Inclua etapas claras para orientar a equipe durante esta rotina."
                icon={<ListChecks className="h-5 w-5" />}
                title="Este checklist ainda não tem tarefas"
              />
            )}
          </section>
        </>
      )}

      {dialogOpen && selectedChecklist && (
        <Dialog
          description={`Checklist: ${selectedChecklist.title}`}
          onClose={() => setDialogOpen(false)}
          title={editing ? "Editar tarefa" : "Adicionar tarefa"}
        >
          <form className="space-y-4" onSubmit={handleSave}>
            {error && <ErrorBanner message={error} onDismiss={() => setError("")} />}
            <label className="block">
              <span className="form-label">Nome da tarefa</span>
              <input
                autoFocus
                className={inputClass}
                maxLength={200}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, title: event.target.value }))
                }
                placeholder="Ex.: Conferir temperatura dos refrigeradores"
                required
                value={draft.title}
              />
            </label>
            <label className="block">
              <span className="form-label">Descrição</span>
              <textarea
                className={`${inputClass} min-h-24 resize-y`}
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    description: event.target.value,
                  }))
                }
                placeholder="Orientações para a execução..."
                rows={3}
                value={draft.description}
              />
            </label>
            <div className="grid gap-4 sm:grid-cols-[1fr_1.2fr]">
              <label className="block">
                <span className="form-label">Ordem de execução</span>
                <input
                  className={inputClass}
                  min={0}
                  onChange={(event) =>
                    setDraft((current) => ({
                      ...current,
                      position: event.target.value,
                    }))
                  }
                  required
                  type="number"
                  value={draft.position}
                />
              </label>
              <label className="flex items-center gap-3 rounded-xl bg-slate-50 px-3.5 py-3 sm:mt-6">
                <input
                  checked={draft.is_required}
                  className="h-4 w-4 accent-leaf"
                  onChange={(event) =>
                    setDraft((current) => ({
                      ...current,
                      is_required: event.target.checked,
                    }))
                  }
                  type="checkbox"
                />
                <span>
                  <span className="block text-sm font-semibold text-ink">
                    Tarefa obrigatória
                  </span>
                  <span className="mt-0.5 block text-xs text-muted">
                    Bloqueia a finalização enquanto estiver pendente.
                  </span>
                </span>
              </label>
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
              <button
                className={buttonSecondary}
                onClick={() => setDialogOpen(false)}
                type="button"
              >
                Cancelar
              </button>
              <button className={buttonPrimary} disabled={saving} type="submit">
                {saving ? "Salvando..." : editing ? "Salvar alterações" : "Adicionar tarefa"}
              </button>
            </div>
          </form>
        </Dialog>
      )}
    </>
  );
}
