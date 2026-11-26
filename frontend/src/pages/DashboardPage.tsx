import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowUpRight,
  CheckCircle2,
  ClipboardList,
  ListTodo,
  RefreshCw,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Link } from "react-router-dom";
import { errorMessage, kitchenApi } from "../lib/api";
import { lastSevenDateKeys, operationDateKey, shortDayLabel } from "../lib/format";
import type { Checklist, ChecklistExecution } from "../types";
import {
  EmptyState,
  ErrorBanner,
  LoadingState,
  PageHeader,
  ProgressBar,
  StatusBadge,
  buttonSecondary,
} from "../components/ui";

interface DashboardData {
  checklists: Checklist[];
  executions: ChecklistExecution[];
}

export function DashboardPage() {
  const [data, setData] = useState<DashboardData>({
    checklists: [],
    executions: [],
  });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const loadData = useCallback(async (quiet = false) => {
    if (quiet) setRefreshing(true);
    else setLoading(true);
    setError("");
    try {
      const [checklists, executions] = await Promise.all([
        kitchenApi.listChecklists(),
        kitchenApi.listExecutions(0, 100),
      ]);
      setData({ checklists, executions });
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

  const todayKey = operationDateKey();
  const todayExecutions = useMemo(
    () => data.executions.filter((item) => item.execution_date === todayKey),
    [data.executions, todayKey],
  );
  const completedTasks = todayExecutions.reduce(
    (total, execution) =>
      total +
      execution.task_executions.filter((task) => task.is_completed).length,
    0,
  );
  const pendingTasks = todayExecutions.reduce(
    (total, execution) =>
      total +
      execution.task_executions.filter((task) => !task.is_completed).length,
    0,
  );
  const checklistNames = useMemo(
    () => new Map(data.checklists.map((item) => [item.id, item.title])),
    [data.checklists],
  );
  const chartData = useMemo(() => {
    const keys = lastSevenDateKeys();
    return keys.map((date) => {
      const executions = data.executions.filter(
        (execution) => execution.execution_date === date,
      );
      const totalTasks = executions.reduce(
        (total, execution) => total + execution.task_executions.length,
        0,
      );
      const completed = executions.reduce(
        (total, execution) =>
          total +
          execution.task_executions.filter((task) => task.is_completed).length,
        0,
      );
      return {
        date: shortDayLabel(date),
        completion: totalTasks ? Math.round((completed / totalTasks) * 100) : 0,
        executions: executions.length,
      };
    });
  }, [data.executions]);

  const stats = [
    {
      label: "Checklists cadastrados",
      value: data.checklists.length,
      hint: `${data.checklists.filter((item) => item.is_active).length} ativos`,
      icon: ClipboardList,
      color: "bg-emerald-50 text-emerald-700",
    },
    {
      label: "Execuções de hoje",
      value: todayExecutions.length,
      hint: `${todayExecutions.filter((item) => item.status === "completed").length} finalizadas`,
      icon: Activity,
      color: "bg-blue-50 text-blue-700",
    },
    {
      label: "Tarefas concluídas",
      value: completedTasks,
      hint: "nas execuções de hoje",
      icon: CheckCircle2,
      color: "bg-lime-50 text-lime-700",
    },
    {
      label: "Pendências",
      value: pendingTasks,
      hint: "tarefas ainda abertas",
      icon: ListTodo,
      color: "bg-amber-50 text-amber-700",
    },
  ];

  return (
    <>
      <PageHeader
        eyebrow="Painel de controle"
        title="Visão geral"
        description="Acompanhe o ritmo da operação e os pontos que precisam de atenção."
        action={
          <button
            className={buttonSecondary}
            disabled={refreshing}
            onClick={() => void loadData(true)}
            type="button"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            Atualizar
          </button>
        }
      />

      {error && <ErrorBanner message={error} onDismiss={() => setError("")} />}

      {loading ? (
        <LoadingState />
      ) : (
        <>
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {stats.map((stat) => {
              const Icon = stat.icon;
              return (
                <article
                  className="rounded-2xl border border-slate-100 bg-white p-5 shadow-card"
                  key={stat.label}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-xs font-medium text-muted">{stat.label}</p>
                      <p className="mt-3 text-3xl font-bold tracking-tight text-ink">
                        {stat.value}
                      </p>
                    </div>
                    <div className={`grid h-10 w-10 place-items-center rounded-xl ${stat.color}`}>
                      <Icon className="h-[18px] w-[18px]" />
                    </div>
                  </div>
                  <p className="mt-4 text-[11px] text-muted">{stat.hint}</p>
                </article>
              );
            })}
          </section>

          <section className="mt-5 grid gap-5 xl:grid-cols-[1.6fr_1fr]">
            <article className="rounded-2xl border border-slate-100 bg-white p-5 shadow-card sm:p-6">
              <div className="mb-5 flex items-start justify-between gap-3">
                <div>
                  <h2 className="font-bold text-ink">Ritmo da operação</h2>
                  <p className="mt-1 text-xs text-muted">
                    Percentual de tarefas concluídas nos últimos 7 dias
                  </p>
                </div>
                <span className="rounded-lg bg-mint px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-leaf">
                  Últimos 7 dias
                </span>
              </div>
              <div className="h-[250px] w-full">
                {data.executions.length ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 10, right: 4, left: -18, bottom: 0 }}>
                      <defs>
                        <linearGradient id="completionFill" x1="0" x2="0" y1="0" y2="1">
                          <stop offset="0%" stopColor="#38966e" stopOpacity={0.22} />
                          <stop offset="95%" stopColor="#38966e" stopOpacity={0.01} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid stroke="#eef1ef" strokeDasharray="4 5" vertical={false} />
                      <XAxis
                        axisLine={false}
                        dataKey="date"
                        tick={{ fill: "#87918b", fontSize: 11 }}
                        tickLine={false}
                      />
                      <YAxis
                        axisLine={false}
                        domain={[0, 100]}
                        tick={{ fill: "#87918b", fontSize: 11 }}
                        tickLine={false}
                        unit="%"
                      />
                      <Tooltip
                        contentStyle={{
                          border: "1px solid #e8eee9",
                          borderRadius: 12,
                          boxShadow: "0 8px 24px rgba(27,55,42,.1)",
                          fontSize: 12,
                        }}
                        formatter={(value) => [`${value}%`, "Conclusão"]}
                      />
                      <Area
                        activeDot={{ r: 5, fill: "#27845e", stroke: "white", strokeWidth: 3 }}
                        dataKey="completion"
                        fill="url(#completionFill)"
                        stroke="#38966e"
                        strokeWidth={3}
                        type="monotone"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <EmptyState
                    description="Assim que houver execuções, o desempenho da semana aparecerá aqui."
                    icon={<Activity className="h-5 w-5" />}
                    title="Sem dados de desempenho"
                  />
                )}
              </div>
            </article>

            <article className="rounded-2xl border border-slate-100 bg-white p-5 shadow-card sm:p-6">
              <div className="mb-5">
                <h2 className="font-bold text-ink">Execuções por dia</h2>
                <p className="mt-1 text-xs text-muted">Atividade recente</p>
              </div>
              <div className="h-[250px]">
                {data.executions.length ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 8, right: 0, left: -22, bottom: 0 }}>
                      <CartesianGrid stroke="#eef1ef" strokeDasharray="4 5" vertical={false} />
                      <XAxis
                        axisLine={false}
                        dataKey="date"
                        tick={{ fill: "#87918b", fontSize: 10 }}
                        tickLine={false}
                      />
                      <YAxis
                        allowDecimals={false}
                        axisLine={false}
                        tick={{ fill: "#87918b", fontSize: 10 }}
                        tickLine={false}
                      />
                      <Tooltip
                        contentStyle={{
                          border: "1px solid #e8eee9",
                          borderRadius: 12,
                          fontSize: 12,
                        }}
                      />
                      <Bar dataKey="executions" fill="#8fcaa6" maxBarSize={24} radius={[6, 6, 2, 2]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <EmptyState
                    description="As execuções iniciadas serão contabilizadas neste gráfico."
                    icon={<ClipboardList className="h-5 w-5" />}
                    title="Nenhuma execução registrada"
                  />
                )}
              </div>
            </article>
          </section>

          <section className="mt-5 rounded-2xl border border-slate-100 bg-white p-5 shadow-card sm:p-6">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <h2 className="font-bold text-ink">Atividade recente</h2>
                <p className="mt-1 text-xs text-muted">
                  Últimas execuções registradas no sistema
                </p>
              </div>
              <Link
                className="inline-flex items-center gap-1 text-xs font-semibold text-leaf hover:text-forest"
                to="/history"
              >
                Ver histórico <ArrowUpRight className="h-3.5 w-3.5" />
              </Link>
            </div>
            {data.executions.length ? (
              <div className="divide-y divide-slate-100">
                {data.executions.slice(0, 5).map((execution) => (
                  <div
                    className="grid gap-3 py-4 sm:grid-cols-[1.4fr_.8fr_1fr] sm:items-center"
                    key={execution.id}
                  >
                    <div>
                      <p className="text-sm font-semibold text-ink">
                        {checklistNames.get(execution.checklist_id) ??
                          `Checklist #${execution.checklist_id}`}
                      </p>
                      <p className="mt-1 text-xs text-muted">
                        {execution.execution_date} · Execução #{execution.id}
                      </p>
                    </div>
                    <div className="sm:justify-self-start">
                      <StatusBadge status={execution.status} />
                    </div>
                    <div className="sm:min-w-36">
                      <ProgressBar value={execution.completion_percentage} />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                action={
                  <Link className={buttonSecondary} to="/checklists">
                    Criar primeiro checklist
                  </Link>
                }
                description="Cadastre uma rotina e inicie a primeira execução para acompanhar a cozinha por aqui."
                icon={<ClipboardList className="h-5 w-5" />}
                title="Sua operação começa aqui"
              />
            )}
          </section>
        </>
      )}
    </>
  );
}
