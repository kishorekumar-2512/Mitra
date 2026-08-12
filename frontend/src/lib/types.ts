export type ChartType = "bar" | "line" | "pie" | "scatter";
export interface ChartSpec { type: ChartType; title: string; data: Record<string, unknown>[]; x_field: string; y_field: string; }
export interface QueryTable { columns: string[]; rows: Record<string, unknown>[]; row_count: number; truncated?: boolean; }
export interface ChatStage { label: string; state: "active" | "complete"; }
export interface ChatAction { label: string; prompt: string; }
export interface ChatMessage { id: string; role: "user" | "assistant"; text: string; sql?: string; table?: QueryTable; chart?: ChartSpec; diagram?: string; status?: string; stages?: ChatStage[]; actions?: ChatAction[]; }
export interface StreamEvent { event: string; data: Record<string, unknown>; }
