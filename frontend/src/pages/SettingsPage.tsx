import { useState, type FormEvent } from "react";
import {
  CheckCircle2,
  ExternalLink,
  KeyRound,
  LockKeyhole,
  Radio,
  RefreshCw,
  Server,
  ShieldCheck,
} from "lucide-react";
import { apiBaseUrl, errorMessage, getStoredApiKey, kitchenApi } from "../lib/api";
import {
  ErrorBanner,
  PageHeader,
  SuccessMessage,
  buttonPrimary,
  buttonSecondary,
  inputClass,
} from "../components/ui";

const operationTimezone =
  import.meta.env.VITE_OPERATION_TIMEZONE || "America/Sao_Paulo";

export function SettingsPage({
  onApiKeyChange,
  onLogout,
}: {
  onApiKeyChange: (key: string) => Promise<void>;
  onLogout: () => void;
}) {
  const [newApiKey, setNewApiKey] = useState("");
  const [savingKey, setSavingKey] = useState(false);
  const [checking, setChecking] = useState(false);
  const [apiStatus, setApiStatus] = useState<"unknown" | "online" | "offline">(
    "unknown",
  );
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function checkApi() {
    setChecking(true);
    setError("");
    try {
      await kitchenApi.health();
      setApiStatus("online");
    } catch (requestError) {
      setApiStatus("offline");
      setError(errorMessage(requestError));
    } finally {
      setChecking(false);
    }
  }

  async function saveApiKey(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const candidate = newApiKey.trim();
    if (!candidate) return;
    setSavingKey(true);
    setError("");
    setSuccess("");
    try {
      await onApiKeyChange(candidate);
      setNewApiKey("");
      setSuccess("A chave foi validada e atualizada para esta sessão.");
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setSavingKey(false);
    }
  }

  const connected = apiStatus === "online";

  return (
    <>
      <PageHeader
        eyebrow="Preferências do sistema"
        title="Configurações"
        description="Consulte os serviços conectados e gerencie o acesso administrativo."
        action={
          <button
            className={buttonSecondary}
            disabled={checking}
            onClick={() => void checkApi()}
            type="button"
          >
            <RefreshCw className={`h-4 w-4 ${checking ? "animate-spin" : ""}`} />
            Verificar API
          </button>
        }
      />
      {error && <ErrorBanner message={error} onDismiss={() => setError("")} />}
      {success && <SuccessMessage>{success}</SuccessMessage>}

      <div className="grid gap-5 xl:grid-cols-[1.2fr_.8fr]">
        <section className="space-y-5">
          <article className="rounded-2xl border border-slate-100 bg-white p-5 shadow-card sm:p-6">
            <div className="flex items-start gap-4">
              <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-mint text-leaf">
                <Server className="h-5 w-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="font-bold text-ink">API KitchenCheck</h2>
                    <p className="mt-1 text-xs text-muted">
                      Backend FastAPI responsável pelos dados operacionais.
                    </p>
                  </div>
                  <span
                    className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                      connected
                        ? "bg-emerald-50 text-emerald-700"
                        : apiStatus === "offline"
                          ? "bg-rose-50 text-rose-700"
                          : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    <span className="h-1.5 w-1.5 rounded-full bg-current" />
                    {connected
                      ? "Disponível"
                      : apiStatus === "offline"
                        ? "Indisponível"
                        : "Não verificada"}
                  </span>
                </div>
                <dl className="mt-5 grid gap-4 border-t border-slate-100 pt-4 sm:grid-cols-2">
                  <div>
                    <dt className="text-[10px] font-bold uppercase tracking-wide text-slate-400">
                      URL utilizada pelo navegador
                    </dt>
                    <dd className="mt-1.5 break-all font-mono text-xs text-ink">
                      {apiBaseUrl}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[10px] font-bold uppercase tracking-wide text-slate-400">
                      Fuso operacional
                    </dt>
                    <dd className="mt-1.5 text-sm font-medium text-ink">
                      {operationTimezone}
                    </dd>
                  </div>
                </dl>
                <a
                  className="mt-4 inline-flex items-center gap-1.5 text-xs font-semibold text-leaf hover:text-forest"
                  href={`${apiBaseUrl}/docs`}
                  rel="noreferrer"
                  target="_blank"
                >
                  Abrir documentação da API
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </div>
            </div>
          </article>

          <article className="rounded-2xl border border-slate-100 bg-white p-5 shadow-card sm:p-6">
            <div className="flex items-start gap-4">
              <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-blue-50 text-blue-700">
                <KeyRound className="h-5 w-5" />
              </div>
              <div className="flex-1">
                <h2 className="font-bold text-ink">Chave administrativa</h2>
                <p className="mt-1 text-xs leading-5 text-muted">
                  A chave é enviada no header <code>X-API-Key</code> e permanece
                  somente na sessão atual deste navegador.
                </p>
                <form className="mt-5 space-y-3" onSubmit={saveApiKey}>
                  <label className="block">
                    <span className="form-label">Substituir chave</span>
                    <input
                      autoComplete="new-password"
                      className={inputClass}
                      onChange={(event) => setNewApiKey(event.target.value)}
                      placeholder="Digite a nova chave administrativa"
                      type="password"
                      value={newApiKey}
                    />
                  </label>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <span className="inline-flex items-center gap-1.5 text-[11px] text-muted">
                      <LockKeyhole className="h-3.5 w-3.5" />
                      {getStoredApiKey()
                        ? "Chave configurada nesta sessão"
                        : "Nenhuma chave salva nesta sessão"}
                    </span>
                    <button
                      className={buttonPrimary}
                      disabled={!newApiKey.trim() || savingKey}
                      type="submit"
                    >
                      {savingKey ? "Validando..." : "Validar e salvar"}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </article>
        </section>

        <section className="space-y-5">
          <article className="rounded-2xl border border-slate-100 bg-white p-5 shadow-card sm:p-6">
            <div className="flex items-start gap-4">
              <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-sky-50 text-sky-700">
                <Radio className="h-5 w-5" />
              </div>
              <div>
                <h2 className="font-bold text-ink">Notificações Telegram</h2>
                <p className="mt-1 text-xs leading-5 text-muted">
                  O envio é realizado pelo serviço de automação. As credenciais
                  são configuradas no servidor e não são expostas nesta interface.
                </p>
              </div>
            </div>
            <div className="mt-5 rounded-xl border border-slate-100 bg-slate-50 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-ink">
                <ShieldCheck className="h-4 w-4 text-leaf" />
                Configuração protegida no servidor
              </div>
              <p className="mt-2 text-xs leading-5 text-muted">
                O backend não disponibiliza um endpoint de status do Telegram.
                Por segurança, esta página não afirma se o bot está conectado e
                não mostra token ou chat ID.
              </p>
            </div>
            <div className="mt-4 flex items-center gap-2 text-[11px] text-muted">
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              Alertas e resumos são processados pelo serviço de automação.
            </div>
          </article>

          <article className="rounded-2xl border border-emerald-100 bg-gradient-to-br from-forest to-[#215641] p-5 text-white shadow-card sm:p-6">
            <p className="text-[10px] font-bold uppercase tracking-[.16em] text-emerald-200">
              KitchenCheck
            </p>
            <h2 className="mt-2 text-lg font-bold">Rotina clara. Cozinha segura.</h2>
            <p className="mt-2 text-xs leading-5 text-white/65">
              Checklists, tarefas e histórico operacional em um só lugar.
            </p>
            <button
              className="mt-5 rounded-lg border border-white/20 px-3 py-2 text-xs font-semibold text-white/85 transition hover:bg-white/10 hover:text-white"
              onClick={onLogout}
              type="button"
            >
              Encerrar sessão administrativa
            </button>
          </article>
        </section>
      </div>
    </>
  );
}
