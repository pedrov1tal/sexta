import { lazy, Suspense, useEffect, useState, type FormEvent } from "react";
import {
  Activity,
  ChefHat,
  ClipboardList,
  Clock3,
  LayoutDashboard,
  ListChecks,
  Menu,
  Settings,
  ShieldCheck,
  X,
} from "lucide-react";
import {
  BrowserRouter,
  Navigate,
  NavLink,
  Route,
  Routes,
} from "react-router-dom";
import {
  clearStoredApiKey,
  errorMessage,
  getStoredApiKey,
  kitchenApi,
  storeApiKey,
} from "./lib/api";
import { LoadingState, buttonPrimary, inputClass } from "./components/ui";
import type { LucideIcon } from "lucide-react";
import { operationTimezone } from "./lib/format";

const DashboardPage = lazy(() =>
  import("./pages/DashboardPage").then((module) => ({
    default: module.DashboardPage,
  })),
);
const ChecklistsPage = lazy(() =>
  import("./pages/ChecklistsPage").then((module) => ({
    default: module.ChecklistsPage,
  })),
);
const TasksPage = lazy(() =>
  import("./pages/TasksPage").then((module) => ({
    default: module.TasksPage,
  })),
);
const ExecutionsPage = lazy(() =>
  import("./pages/ExecutionsPage").then((module) => ({
    default: module.ExecutionsPage,
  })),
);
const HistoryPage = lazy(() =>
  import("./pages/HistoryPage").then((module) => ({
    default: module.HistoryPage,
  })),
);
const SettingsPage = lazy(() =>
  import("./pages/SettingsPage").then((module) => ({
    default: module.SettingsPage,
  })),
);

type AuthState = "checking" | "required" | "ready";

interface NavigationItem {
  label: string;
  path: string;
  icon: LucideIcon;
}

const navigation: NavigationItem[] = [
  { label: "Visão geral", path: "/", icon: LayoutDashboard },
  { label: "Checklists", path: "/checklists", icon: ClipboardList },
  { label: "Tarefas", path: "/tasks", icon: ListChecks },
  { label: "Execuções", path: "/executions", icon: Activity },
  { label: "Histórico", path: "/history", icon: Clock3 },
];

function AuthGate() {
  const [authState, setAuthState] = useState<AuthState>(
    getStoredApiKey() ? "checking" : "required",
  );
  const [error, setError] = useState("");

  useEffect(() => {
    const storedKey = getStoredApiKey();
    if (!storedKey) return;

    kitchenApi
      .listChecklists()
      .then(() => setAuthState("ready"))
      .catch((requestError: unknown) => {
        clearStoredApiKey();
        setError(errorMessage(requestError));
        setAuthState("required");
      });
  }, []);

  async function authenticate(candidate: string): Promise<void> {
    setError("");
    storeApiKey(candidate);
    try {
      await kitchenApi.listChecklists();
      setAuthState("ready");
    } catch (requestError) {
      clearStoredApiKey();
      setError(errorMessage(requestError));
      setAuthState("required");
    }
  }

  async function changeApiKey(candidate: string): Promise<void> {
    const previousKey = getStoredApiKey();
    storeApiKey(candidate);
    try {
      await kitchenApi.listChecklists();
    } catch (requestError) {
      if (previousKey) storeApiKey(previousKey);
      else clearStoredApiKey();
      throw requestError;
    }
  }

  function logout(): void {
    clearStoredApiKey();
    setAuthState("required");
    setError("");
  }

  if (authState === "checking") {
    return (
      <div className="grid min-h-screen place-items-center bg-canvas">
        <LoadingState label="Validando acesso ao KitchenCheck..." />
      </div>
    );
  }

  if (authState === "required") {
    return <AccessPage error={error} onAuthenticate={authenticate} />;
  }

  return (
    <AppShell onApiKeyChange={changeApiKey} onLogout={logout} />
  );
}

function AccessPage({
  error,
  onAuthenticate,
}: {
  error: string;
  onAuthenticate: (key: string) => Promise<void>;
}) {
  const [apiKey, setApiKey] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [localError, setLocalError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setLocalError("");
    try {
      await onAuthenticate(apiKey.trim());
    } catch {
      setLocalError("Não foi possível validar a chave.");
    } finally {
      setSubmitting(false);
    }
  }

  const visibleError = localError || error;

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-canvas px-5 py-12">
      <div className="absolute -left-24 -top-28 h-80 w-80 rounded-full bg-emerald-100/70 blur-3xl" />
      <div className="absolute -bottom-32 -right-20 h-96 w-96 rounded-full bg-lime-100/70 blur-3xl" />
      <section className="relative z-10 w-full max-w-md rounded-3xl border border-white bg-white p-7 shadow-float sm:p-9">
        <div className="mb-8 flex items-center gap-3">
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-forest text-emerald-100">
            <ChefHat className="h-6 w-6" />
          </div>
          <div>
            <p className="text-lg font-bold tracking-tight text-ink">
              Kitchen<span className="text-leaf">Check</span>
            </p>
            <p className="text-xs text-muted">Gestão operacional da cozinha</p>
          </div>
        </div>
        <div className="mb-7">
          <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-mint text-leaf">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">
            Acesso administrativo
          </h1>
          <p className="mt-2 text-sm leading-6 text-muted">
            Informe a chave administrativa configurada no servidor para acessar
            os checklists e execuções.
          </p>
        </div>
        {visibleError && (
          <div
            role="alert"
            className="mb-5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
          >
            {visibleError}
          </div>
        )}
        <form className="space-y-4" onSubmit={handleSubmit}>
          <label className="block">
            <span className="mb-2 block text-sm font-semibold text-ink">
              Chave de API
            </span>
            <input
              autoComplete="current-password"
              className={inputClass}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder="ADMIN_API_KEY"
              required
              type="password"
              value={apiKey}
            />
          </label>
          <button className={`${buttonPrimary} w-full`} disabled={submitting}>
            {submitting ? "Validando..." : "Entrar no painel"}
          </button>
        </form>
        <p className="mt-5 text-center text-xs leading-5 text-muted">
          A chave fica somente nesta sessão do navegador e é enviada no header
          <code className="mx-1 rounded bg-slate-100 px-1.5 py-0.5 text-[11px]">
            X-API-Key
          </code>
          .
        </p>
      </section>
    </main>
  );
}

function AppShell({
  onApiKeyChange,
  onLogout,
}: {
  onApiKeyChange: (key: string) => Promise<void>;
  onLogout: () => void;
}) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [apiConnected, setApiConnected] = useState<boolean | null>(null);

  useEffect(() => {
    kitchenApi
      .health()
      .then(() => setApiConnected(true))
      .catch(() => setApiConnected(false));
  }, []);

  function closeMenu() {
    setMobileMenuOpen(false);
  }

  return (
    <div className="min-h-screen bg-canvas">
      {mobileMenuOpen && (
        <button
          aria-label="Fechar menu"
          className="fixed inset-0 z-30 bg-slate-950/40 md:hidden"
          onClick={closeMenu}
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-[260px] flex-col bg-forest text-white transition-transform duration-300 md:translate-x-0 ${mobileMenuOpen ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="flex h-[84px] items-center justify-between border-b border-white/10 px-6">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-white/10 text-emerald-100">
              <ChefHat className="h-5 w-5" />
            </div>
            <div>
              <p className="font-bold tracking-tight">
                Kitchen<span className="text-emerald-300">Check</span>
              </p>
              <p className="mt-0.5 text-[10px] uppercase tracking-[.18em] text-white/50">
                Painel operacional
              </p>
            </div>
          </div>
          <button
            aria-label="Fechar menu"
            className="rounded-lg p-2 text-white/60 hover:bg-white/10 md:hidden"
            onClick={closeMenu}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="px-4 pt-7">
          <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[.18em] text-white/40">
            Menu principal
          </p>
          <nav className="space-y-1">
            {navigation.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  end={item.path === "/"}
                  onClick={closeMenu}
                  to={item.path}
                  className={({ isActive }) =>
                    `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium transition ${
                      isActive
                        ? "bg-white text-forest shadow-sm"
                        : "text-white/70 hover:bg-white/10 hover:text-white"
                    }`
                  }
                >
                  <Icon className="h-[17px] w-[17px]" />
                  {item.label}
                  {item.path === "/executions" && (
                    <span className="ml-auto rounded-full bg-emerald-400/20 px-2 py-0.5 text-[10px] font-bold text-emerald-200">
                      LIVE
                    </span>
                  )}
                </NavLink>
              );
            })}
          </nav>
        </div>

        <div className="mt-auto p-4">
          <div className="rounded-2xl border border-white/10 bg-white/[.06] p-4">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs font-semibold text-white/85">
                Conexão com a API
              </span>
              <span
                className={`h-2 w-2 rounded-full ${apiConnected ? "bg-emerald-400 shadow-[0_0_0_4px_rgba(52,211,153,.13)]" : "bg-rose-400"}`}
              />
            </div>
            <p className="text-[11px] leading-5 text-white/50">
              {apiConnected === null
                ? "Verificando serviço..."
                : apiConnected
                  ? "Serviço disponível"
                  : "API indisponível"}
            </p>
            <NavLink
              className="mt-3 flex items-center gap-2 text-xs font-medium text-emerald-200 hover:text-white"
              onClick={closeMenu}
              to="/settings"
            >
              <Settings className="h-3.5 w-3.5" />
              Configurações
            </NavLink>
          </div>
          <div className="mt-4 flex items-center gap-3 px-2 py-2">
            <div className="grid h-9 w-9 place-items-center rounded-full bg-emerald-200 text-xs font-bold text-forest">
              KC
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-semibold text-white">Administrador</p>
              <p className="text-[10px] text-white/45">Acesso local</p>
            </div>
            <button
              className="text-[10px] font-semibold text-white/50 hover:text-white"
              onClick={onLogout}
              type="button"
            >
              Sair
            </button>
          </div>
        </div>
      </aside>

      <div className="min-h-screen md:pl-[260px]">
        <header className="sticky top-0 z-20 flex h-[72px] items-center justify-between border-b border-slate-200/80 bg-white/90 px-4 backdrop-blur-md sm:px-7 lg:px-10">
          <div className="flex items-center gap-3">
            <button
              aria-label="Abrir menu"
              className="rounded-xl border border-slate-200 p-2 text-ink md:hidden"
              onClick={() => setMobileMenuOpen(true)}
            >
              <Menu className="h-5 w-5" />
            </button>
            <div>
              <p className="text-xs font-semibold text-ink sm:text-sm">
                Operação da cozinha
              </p>
              <p className="mt-0.5 hidden text-[11px] text-muted sm:block">
                Acompanhe a rotina e mantenha tudo em ordem
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-xs font-semibold text-ink">Turno de hoje</p>
              <p className="mt-0.5 text-[11px] text-muted">
                {new Intl.DateTimeFormat("pt-BR", {
                  weekday: "long",
                  day: "2-digit",
                  month: "long",
                  timeZone: operationTimezone,
                }).format(new Date())}
              </p>
            </div>
            <div className="grid h-9 w-9 place-items-center rounded-full bg-mint text-xs font-bold text-forest">
              KC
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-[1500px] px-4 py-7 sm:px-7 lg:px-10 lg:py-9">
          <Suspense fallback={<LoadingState label="Carregando página..." />}>
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/checklists" element={<ChecklistsPage />} />
              <Route path="/tasks" element={<TasksPage />} />
              <Route path="/executions" element={<ExecutionsPage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route
                path="/settings"
                element={
                  <SettingsPage
                    onApiKeyChange={onApiKeyChange}
                    onLogout={onLogout}
                  />
                }
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </main>
        <footer className="px-4 pb-6 text-center text-[11px] text-slate-400 sm:px-7 lg:px-10">
          KitchenCheck · Rotinas mais seguras, cozinha mais organizada
        </footer>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthGate />
    </BrowserRouter>
  );
}
