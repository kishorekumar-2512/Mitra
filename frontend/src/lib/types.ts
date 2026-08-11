export type ChartType = "bar" | "line" | "pie" | "scatter";
export interface ChartSpec { type: ChartType; title: string; data: Record<string, unknown>[]; x_field: string; y_field: string; }
export interface ChatMessage { id: string; role: "user" | "assistant"; text: string; sql?: string; chart?: ChartSpec; diagram?: string; status?: string; }
export interface StreamEvent { event: string; data: Record<string, unknown>; }
