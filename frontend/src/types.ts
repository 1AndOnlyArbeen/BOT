export type Mode = "ultron" | "chat" | "coder";

export interface Session {
  id: number;
  title: string;
  created_at: number;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
}

export type StreamEvent =
  | { type: "router"; data: { categories: string[]; tool_count: number } }
  | { type: "plan"; data: { request: string; steps: PlanStep[] } }
  | { type: "step_start"; data: { index: number; goal: string; categories: string[]; tool_count: number } }
  | { type: "step_end"; data: { index: number; status: string; result: string } }
  | { type: "tool_call"; data: { name: string; args: string } }
  | { type: "tool_result"; data: { name: string; content: string } }
  | { type: "token"; data: string }
  | { type: "final"; data: string }
  | { type: "plan_done"; data: { summary: string } }
  | { type: "abort"; data: { reason: string } }
  | { type: "error"; data: string };

export interface PlanStep {
  index: number;
  goal: string;
  rationale?: string;
}

export interface Memory {
  text: string;
  created_at: number;
}

export interface Macro {
  name: string;
  prompt: string;
  description: string;
  runs: number;
  created_at: number;
}

export interface Task {
  id: number;
  title: string;
  due: number | null;
  project: string | null;
  priority: string | null;
  status: string;
  created_at: number;
}

export interface FileNode {
  path: string;
  is_dir: boolean;
}

export interface AuditEntry {
  id: number;
  ts: number;
  tool: string;
  args: string | null;
  result: string;
  duration_ms: number;
  status: string;
}

export interface ToolInfo {
  name: string;
  description: string;
  tier: string;
}
