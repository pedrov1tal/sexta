import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import {
  Clock3,
  ClipboardList,
  Edit3,
  Plus,
  Search,
  Trash2,
  Utensils,
} from "lucide-react";
import { Link } from "react-router-dom";
import { errorMessage, kitchenApi } from "../lib/api";
import { checklistTypeLabels, formatDateTime, formatTime } from "../lib/format";
import type { Checklist, ChecklistPayload, ChecklistType } from "../types";
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

type ChecklistDraft = {
  title: string;
  description: string;
  checklist_type: ChecklistType;
  scheduled_time: string;
  deadline: string;
  is_active: boolean;
};

const emptyDraft: ChecklistDraft = {
  title: "",
  description: "",
  checklist_type: "opening",
  scheduled_time: "",
  deadline: "",
  is_active: true,
};

const typeStyles: Record<ChecklistType, string> = {
  opening: "bg-amber-50 text-amber-700",
  operation: "bg-blue-50 text-blue-700",
  closing: "bg-violet-50 text-violet-700",
};

export function ChecklistsPage() {
  const [checklists, setChecklists] = useState<Checklist[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Checklist | null>(null);
  const [draft, setDraft] = useState<ChecklistDraft>(emptyDraft);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [saving, setSaving] = useState(false);

  const loadChecklists = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setChecklists(await kitchenApi.listChecklists());
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadChecklists();
  }, [loadChecklists]);

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return checklists;
    return checklists.filter((item) =>
      `${item.title} ${item.description ?? ""} ${checklistTypeLabels[item.checklist_type]}`
        .toLowerCase()
        .includes(normalized),
    );
  }, [checklists, query]);

  function openCreate() {
    setEditing(null);
    setDraft(emptyDraft);
    setError("");
    setDialogOpen(true);
  }

  function openEdit(checklist: Checklist) {
    setEditing(checklist);
    setDraft({
      title: checklist.title,
      description: checklist.description ?? "",
      checklist_type: checklist.checklist_type,
      scheduled_time: checklist.scheduled_time?.slice(0, 5) ?? "",
      deadline: checklist.deadline?.slice(0, 5) ?? "",
      is_active: checklist.is_active,
    });
    setError("");
    setDialogOpen(true);
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    const payload: ChecklistPayload = {
      title: draft.title.trim(),
      description: draft.description.trim() || null,
      checklist_type: draft.checklist_type,
      scheduled_time: draft.scheduled_time || null,
      deadline: draft.deadline || null,
      is_active: draft.is_active,
    };
    try {
      if (editing) await kitchenApi.updateChecklist(editing.id, payload);
      else await kitchenApi.createChecklist(payload);
      setDialogOpen(false);
      setSuccess(editing ? "Checklist atualizado com sucesso." : "Checklist criado com sucesso.");
      await loadChecklists();
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(checklist: Checklist) {
    const confirmed = window.confirm(
      `Excluir o checklist "${checklist.title}"? Essa ação não pode ser desfeita.`,
    );
    if (!confirmed) return;
    setError("");
    setSuccess("");
    try {
      await kitchenApi.deleteChecklist(checklist.id);
      setSuccess("Checklist excluído.");
      await loadChecklists();
    } catch (requestError) {
      setError(errorMessage(requestError));
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Rotinas da cozinha"
        title="Checklists"
        description="Organize as rotinas de abertura, operação e fechamento da equipe."
        action={
          <button className={buttonPrimary} onClick={openCreate} type="button">
            <Plus className="h-4 w-4" />
            Novo checklist
          </button>
        }
      />
      {error && <ErrorBanner message={error} onDismiss={() => setError("")} />}
      {success && <SuccessMessage>{success}</SuccessMessage>}

      <section className="rounded-2xl border border-slate-100 bg-white p-4 shadow-card sm:p-5">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div className="relative min-w-[220px] flex-1 sm:max-w-sm">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              className={`${inputClass} pl-9`}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Buscar por nome ou tipo..."
              value={query}
            />
          </div>
          <span className="text-xs text-muted">
            {checklists.length} {checklists.length === 1 ? "rotina" : "rotinas"}
          </span>
        </div>

        {loading ? (
          <LoadingState label="Carregando checklists..." />
        ) : filtered.length ? (
          <div className="grid gap-4 lg:grid-cols-2 2xl:grid-cols-3">
            {filtered.map((checklist) => (
              <article
                className="group rounded-2xl border border-slate-100 p-5 transition hover:border-emerald-200 hover:shadow-card"
                key={checklist.id}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-start gap-3">
                    <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-mint text-leaf">
                      <Utensils className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <h2 className="truncate font-bold text-ink">
                        {checklist.title}
                      </h2>
                      <p className="mt-1 text-xs text-muted">
                        {checklist.tasks.length}{" "}
                        {checklist.tasks.length === 1 ? "tarefa" : "tarefas"}
                      </p>
                    </div>
                  </div>
                  <span
                    className={`shrink-0 rounded-full px-2.5 py-1 text-[10px] font-bold ${typeStyles[checklist.checklist_type]}`}
                  >
                    {checklistTypeLabels[checklist.checklist_type]}
                  </span>
                </div>

                <p className="mt-4 min-h-10 text-sm leading-5 text-muted">
                  {checklist.description || "Sem descrição cadastrada."}
                </p>

                <div className="mt-4 flex flex-wrap gap-2">
                  <span className="inline-flex items-center gap-1.5 rounded-lg bg-slate-50 px-2.5 py-1.5 text-xs text-slate-600">
                    <Clock3 className="h-3.5 w-3.5 text-muted" />
                    Início {formatTime(checklist.scheduled_time)}
                  </span>
                  <span className="inline-flex items-center gap-1.5 rounded-lg bg-slate-50 px-2.5 py-1.5 text-xs text-slate-600">
                    Prazo {formatTime(checklist.deadline)}
                  </span>
                  <span
                    className={`rounded-lg px-2.5 py-1.5 text-xs font-medium ${
                      checklist.is_active
                        ? "bg-emerald-50 text-emerald-700"
                        : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {checklist.is_active ? "Ativo" : "Inativo"}
                  </span>
                </div>

                <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4">
                  <p className="text-[10px] text-slate-400">
                    Atualizado {formatDateTime(checklist.updated_at)}
                  </p>
                  <div className="flex items-center gap-1">
                    <Link
                      aria-label={`Gerenciar tarefas de ${checklist.title}`}
                      className="rounded-lg p-2 text-muted transition hover:bg-mint hover:text-leaf"
                      title="Gerenciar tarefas"
                      to={`/tasks?checklist_id=${checklist.id}`}
                    >
                      <ClipboardList className="h-4 w-4" />
                    </Link>
                    <button
                      aria-label={`Editar ${checklist.title}`}
                      className="rounded-lg p-2 text-muted transition hover:bg-blue-50 hover:text-blue-700"
                      onClick={() => openEdit(checklist)}
                      title="Editar"
                      type="button"
                    >
                      <Edit3 className="h-4 w-4" />
                    </button>
                    <button
                      aria-label={`Excluir ${checklist.title}`}
                      className="rounded-lg p-2 text-muted transition hover:bg-rose-50 hover:text-rose-700"
                      onClick={() => void handleDelete(checklist)}
                      title="Excluir"
                      type="button"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState
            action={
              query ? undefined : (
                <button className={buttonPrimary} onClick={openCreate} type="button">
                  <Plus className="h-4 w-4" />
                  Criar checklist
                </button>
              )
            }
            description={
              query
                ? "Tente outra palavra ou confira o tipo de rotina."
                : "Cadastre sua primeira rotina operacional para começar a organizar a cozinha."
            }
            icon={<ClipboardList className="h-5 w-5" />}
            title={query ? "Nenhum resultado encontrado" : "Nenhum checklist ainda"}
          />
        )}
      </section>

      {dialogOpen && (
        <Dialog
          description="Defina a rotina e os horários usados pelo motor de automação."
          onClose={() => setDialogOpen(false)}
          title={editing ? "Editar checklist" : "Novo checklist"}
        >
          <form className="space-y-4" onSubmit={handleSave}>
            {error && <ErrorBanner message={error} onDismiss={() => setError("")} />}
            <label className="block">
              <span className="form-label">Nome da rotina</span>
              <input
                autoFocus
                className={inputClass}
                maxLength={200}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, title: event.target.value }))
                }
                placeholder="Ex.: Abertura da cozinha"
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
                placeholder="Descreva o objetivo desta rotina..."
                rows={3}
                value={draft.description}
              />
            </label>
            <label className="block">
              <span className="form-label">Tipo de checklist</span>
              <select
                className={inputClass}
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    checklist_type: event.target.value as ChecklistType,
                  }))
                }
                value={draft.checklist_type}
              >
                <option value="opening">Abertura</option>
                <option value="operation">Operação</option>
                <option value="closing">Fechamento</option>
              </select>
            </label>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="form-label">Horário previsto</span>
                <input
                  className={inputClass}
                  onChange={(event) =>
                    setDraft((current) => ({
                      ...current,
                      scheduled_time: event.target.value,
                    }))
                  }
                  type="time"
                  value={draft.scheduled_time}
                />
              </label>
              <label className="block">
                <span className="form-label">Prazo de conclusão</span>
                <input
                  className={inputClass}
                  onChange={(event) =>
                    setDraft((current) => ({
                      ...current,
                      deadline: event.target.value,
                    }))
                  }
                  type="time"
                  value={draft.deadline}
                />
              </label>
            </div>
            <label className="flex items-center gap-3 rounded-xl bg-slate-50 px-3.5 py-3">
              <input
                checked={draft.is_active}
                className="h-4 w-4 accent-leaf"
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    is_active: event.target.checked,
                  }))
                }
                type="checkbox"
              />
              <span>
                <span className="block text-sm font-semibold text-ink">
                  Checklist ativo
                </span>
                <span className="mt-0.5 block text-xs text-muted">
                  Rotinas ativas podem ser iniciadas pela automação.
                </span>
              </span>
            </label>
            <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
              <button
                className={buttonSecondary}
                onClick={() => setDialogOpen(false)}
                type="button"
              >
                Cancelar
              </button>
              <button className={buttonPrimary} disabled={saving} type="submit">
                {saving ? "Salvando..." : editing ? "Salvar alterações" : "Criar checklist"}
              </button>
            </div>
          </form>
        </Dialog>
      )}
    </>
  );
}
