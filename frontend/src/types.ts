export type ChecklistType = "opening" | "operation" | "closing";
export type ExecutionStatus =
  | "pending"
  | "in_progress"
  | "completed"
  | "overdue";

export interface Task {
  id: number;
  checklist_id: number;
  title: string;
  description: string | null;
  is_required: boolean;
  position: number;
  updated_at: string;
}

export interface Checklist {
  id: number;
  title: string;
  description: string | null;
  checklist_type: ChecklistType;
  scheduled_time: string | null;
  deadline: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  tasks: Task[];
}

export interface ChecklistPayload {
  title: string;
  description: string | null;
  checklist_type: ChecklistType;
  scheduled_time: string | null;
  deadline: string | null;
  is_active: boolean;
}

export interface TaskPayload {
  title: string;
  description: string | null;
  is_required: boolean;
  position: number;
}

export interface TaskExecution {
  id: number;
  task_id: number;
  is_completed: boolean;
  completed_at: string | null;
  updated_at: string;
  task: Task;
}

export interface ChecklistExecution {
  id: number;
  checklist_id: number;
  execution_date: string;
  status: ExecutionStatus;
  started_at: string | null;
  completed_at: string | null;
  updated_at: string;
  task_executions: TaskExecution[];
  completion_percentage: number;
  is_complete: boolean;
  is_incomplete: boolean;
  is_overdue: boolean;
}

export interface ApiHealth {
  status: string;
}
