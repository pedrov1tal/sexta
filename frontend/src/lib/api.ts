import axios, { AxiosError } from "axios";
import type {
  ApiHealth,
  Checklist,
  ChecklistExecution,
  ChecklistPayload,
  Task,
  TaskPayload,
} from "../types";

const API_KEY_STORAGE = "kitchencheck.adminApiKey";
const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL || "/api";

export const apiBaseUrl = configuredBaseUrl.replace(/\/+$/, "");

export const http = axios.create({
  baseURL: apiBaseUrl,
  timeout: 12_000,
  headers: { "Content-Type": "application/json" },
});

http.interceptors.request.use((config) => {
  const key = sessionStorage.getItem(API_KEY_STORAGE);
  if (key) config.headers.set("X-API-Key", key);
  return config;
});

export function getStoredApiKey(): string {
  return sessionStorage.getItem(API_KEY_STORAGE) ?? "";
}

export function storeApiKey(key: string): void {
  sessionStorage.setItem(API_KEY_STORAGE, key);
}

export function clearStoredApiKey(): void {
  sessionStorage.removeItem(API_KEY_STORAGE);
}

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: unknown }>;
    const detail = axiosError.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          typeof item === "object" &&
          item !== null &&
          "msg" in item &&
          typeof item.msg === "string"
            ? item.msg
            : "",
        )
        .filter(Boolean)
        .join(" ");
    }
    if (!axiosError.response) {
      return "Não foi possível conectar à API. Verifique se os serviços estão ativos.";
    }
    return `A API respondeu com erro (${axiosError.response.status}).`;
  }
  return "Ocorreu um erro inesperado. Tente novamente.";
}

export const kitchenApi = {
  health: () => http.get<ApiHealth>("/health").then(({ data }) => data),
  listChecklists: () =>
    http.get<Checklist[]>("/checklists").then(({ data }) => data),
  createChecklist: (payload: ChecklistPayload) =>
    http.post<Checklist>("/checklists", payload).then(({ data }) => data),
  updateChecklist: (id: number, payload: ChecklistPayload) =>
    http.put<Checklist>(`/checklists/${id}`, payload).then(({ data }) => data),
  deleteChecklist: (id: number) => http.delete(`/checklists/${id}`),
  listTasks: (checklistId: number) =>
    http
      .get<Task[]>(`/checklists/${checklistId}/tasks`)
      .then(({ data }) => data),
  createTask: (checklistId: number, payload: TaskPayload) =>
    http
      .post<Task>(`/checklists/${checklistId}/tasks`, payload)
      .then(({ data }) => data),
  updateTask: (id: number, payload: TaskPayload) =>
    http.put<Task>(`/tasks/${id}`, payload).then(({ data }) => data),
  deleteTask: (id: number) => http.delete(`/tasks/${id}`),
  listExecutions: (skip = 0, limit = 100) =>
    http
      .get<ChecklistExecution[]>("/executions", { params: { skip, limit } })
      .then(({ data }) => data),
  startExecution: (checklistId: number) =>
    http
      .post<ChecklistExecution>(`/checklists/${checklistId}/executions`)
      .then(({ data }) => data),
  completeTask: (executionId: number, taskId: number) =>
    http
      .patch<ChecklistExecution>(
        `/executions/${executionId}/tasks/${taskId}`,
      )
      .then(({ data }) => data),
};
