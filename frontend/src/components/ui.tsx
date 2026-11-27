import { useEffect, type ReactNode } from "react";
import { AlertCircle, Check, LoaderCircle, X } from "lucide-react";
import type { ExecutionStatus } from "../types";
import { executionStatusLabels } from "../lib/format";

const statusStyles: Record<ExecutionStatus, string> = {
  pending: "bg-slate-100 text-slate-600",
  in_progress: "bg-blue-50 text-blue-700",
  completed: "bg-emerald-50 text-emerald-700",
  overdue: "bg-rose-50 text-rose-700",
};

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow && (
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[.16em] text-leaf">
            {eyebrow}
          </p>
        )}
        <h1 className="text-[26px] font-bold tracking-tight text-ink sm:text-[30px]">
          {title}
        </h1>
        {description && (
          <p className="mt-1.5 max-w-2xl text-sm text-muted">{description}</p>
        )}
      </div>
      {action}
    </div>
  );
}

export function StatusBadge({ status }: { status: ExecutionStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ${statusStyles[status]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {executionStatusLabels[status]}
    </span>
  );
}

export function ProgressBar({
  value,
  showLabel = true,
}: {
  value: number;
  showLabel?: boolean;
}) {
  const safeValue = Math.min(100, Math.max(0, value));
  return (
    <div className="flex items-center gap-3">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-leaf transition-all duration-500"
          style={{ width: `${safeValue}%` }}
        />
      </div>
      {showLabel && (
        <span className="min-w-9 text-right text-xs font-semibold text-ink">
          {Math.round(safeValue)}%
        </span>
      )}
    </div>
  );
}

export function LoadingState({ label = "Carregando dados..." }: { label?: string }) {
  return (
    <div className="flex min-h-52 flex-col items-center justify-center gap-3 text-sm text-muted">
      <LoaderCircle className="h-6 w-6 animate-spin text-leaf" />
      {label}
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex min-h-56 flex-col items-center justify-center px-5 py-10 text-center">
      <div className="mb-4 grid h-12 w-12 place-items-center rounded-2xl bg-mint text-leaf">
        {icon}
      </div>
      <h3 className="font-semibold text-ink">{title}</h3>
      <p className="mt-1 max-w-sm text-sm leading-6 text-muted">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorBanner({
  message,
  onDismiss,
}: {
  message: string;
  onDismiss?: () => void;
}) {
  return (
    <div
      role="alert"
      className="mb-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
    >
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      <span className="flex-1">{message}</span>
      {onDismiss && (
        <button
          aria-label="Fechar aviso"
          className="rounded p-0.5 hover:bg-rose-100"
          onClick={onDismiss}
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

export function SuccessMessage({ children }: { children: ReactNode }) {
  return (
    <div className="mb-5 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
      <Check className="h-4 w-4 shrink-0" />
      {children}
    </div>
  );
}

export function Dialog({
  title,
  description,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/45 p-0 backdrop-blur-[2px] sm:items-center sm:p-5"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        aria-modal="true"
        className={`max-h-[92vh] w-full overflow-y-auto rounded-t-3xl bg-white p-5 shadow-float sm:rounded-2xl sm:p-7 ${wide ? "max-w-2xl" : "max-w-lg"}`}
        role="dialog"
        aria-labelledby="dialog-title"
      >
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h2 id="dialog-title" className="text-xl font-bold text-ink">
              {title}
            </h2>
            {description && (
              <p className="mt-1 text-sm text-muted">{description}</p>
            )}
          </div>
          <button
            aria-label="Fechar"
            className="rounded-lg p-2 text-muted transition hover:bg-slate-100 hover:text-ink"
            onClick={onClose}
            type="button"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}

export const buttonPrimary =
  "inline-flex items-center justify-center gap-2 rounded-xl bg-forest px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-leaf focus:outline-none focus:ring-4 focus:ring-emerald-100 disabled:cursor-not-allowed disabled:opacity-50";

export const buttonSecondary =
  "inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-emerald-200 hover:bg-mint disabled:cursor-not-allowed disabled:opacity-50";

export const inputClass =
  "w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-ink outline-none transition placeholder:text-slate-400 focus:border-leaf focus:ring-4 focus:ring-emerald-50";
