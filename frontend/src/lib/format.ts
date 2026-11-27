import type { ChecklistType, ExecutionStatus } from "../types";

export const operationTimezone =
  import.meta.env.VITE_OPERATION_TIMEZONE || "America/Sao_Paulo";

export const checklistTypeLabels: Record<ChecklistType, string> = {
  opening: "Abertura",
  operation: "Operação",
  closing: "Fechamento",
};

export const executionStatusLabels: Record<ExecutionStatus, string> = {
  pending: "Pendente",
  in_progress: "Em andamento",
  completed: "Concluído",
  overdue: "Atrasado",
};

export function formatTime(value: string | null): string {
  return value ? value.slice(0, 5) : "—";
}

export function formatDate(value: string): string {
  const date = new Date(`${value}T12:00:00`);
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: operationTimezone,
  }).format(date);
}

export function formatDateTime(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: operationTimezone,
  }).format(new Date(value));
}

export function operationDateKey(date = new Date()): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: operationTimezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

export function lastSevenDateKeys(): string[] {
  const todayKey = operationDateKey();
  const [year, month, day] = todayKey.split("-").map(Number);
  const todayUtc = new Date(Date.UTC(year, month - 1, day));
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(todayUtc);
    date.setUTCDate(date.getUTCDate() - (6 - index));
    return date.toISOString().slice(0, 10);
  });
}

export function shortDayLabel(dateKey: string): string {
  const [year, month, day] = dateKey.split("-").map(Number);
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(year, month - 1, day, 12)));
}
