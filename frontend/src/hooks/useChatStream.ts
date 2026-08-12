import { useCallback, useState } from "react";
import type { ChatAction, ChatMessage, ChartSpec, QueryTable } from "../lib/types";

const api = import.meta.env.VITE_API_URL || "";
export type Provider = "anthropic" | "groq" | "gemini";
export interface ProviderConfig { provider: Provider; apiKey: string; model: string; }

const completeStages = (stages: ChatMessage["stages"] = []) => stages.map(stage => ({ ...stage, state: "complete" as const }));
const addStage = (stages: ChatMessage["stages"] = [], label: string, state: "active" | "complete" = "active") => [
  ...stages.filter(stage => stage.label !== label).map(stage => ({ ...stage, state: "complete" as const })),
  { label, state },
];

export function useChatStream(sessionId: string, providerConfig: ProviderConfig) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);

  const send = useCallback(async (message: string) => {
    setMessages(current => [...current,
      { id: crypto.randomUUID(), role: "user", text: message },
      { id: crypto.randomUUID(), role: "assistant", text: "", status: "Understanding your question…", stages: [{ label: "Understand question", state: "active" }] }
    ]);
    setBusy(true);
    try {
      const response = await fetch(`${api}/api/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: sessionId, message, provider: providerConfig.provider, api_key: providerConfig.apiKey || undefined, model: providerConfig.model || undefined }) });
      if (!response.ok || !response.body) throw new Error("Could not start the analysis stream.");
      const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = ""; let receivedResponse = false;
      const update = (fn: (current: ChatMessage) => ChatMessage) => setMessages(all => all.map((item, i) => i === all.length - 1 ? fn(item) : item));
      while (true) {
        const result = await reader.read(); if (result.done) break; buffer += decoder.decode(result.value, { stream: true });
        const blocks = buffer.split("\n\n"); buffer = blocks.pop() || "";
        for (const block of blocks) {
          const name = block.match(/^event: (.+)$/m)?.[1]; const raw = block.match(/^data: (.+)$/m)?.[1];
          if (!name || !raw) continue;
          const data = JSON.parse(raw);
          if (name === "token") { receivedResponse = true; update(m => ({ ...m, text: m.text + data.text, status: undefined, stages: completeStages(m.stages) })); }
          if (name === "tool_call") update(m => {
            const label = ({ get_schema: "Inspect schema", execute_query: "Generate SQL", generate_chart: "Choose visualization", generate_flowchart: "Build diagram", explain_data: "Explain results" } as Record<string, string>)[data.name] || "Analyze data";
            const status = ({ get_schema: "Inspecting database…", execute_query: "Generating SQL…", generate_chart: "Building chart…", generate_flowchart: "Drawing diagram…", explain_data: "Writing answer…" } as Record<string, string>)[data.name] || "Working…";
            return { ...m, status, stages: addStage(m.stages, label) };
          });
          if (name === "sql") { receivedResponse = true; update(m => ({ ...m, sql: data.sql, status: "Retrieving records…", stages: addStage(addStage(m.stages, "Generate SQL", "complete"), "Retrieve records") })); }
          if (name === "table") { receivedResponse = true; update(m => ({ ...m, table: data as QueryTable, status: undefined, stages: completeStages(m.stages) })); }
          if (name === "chart") { receivedResponse = true; update(m => ({ ...m, chart: data as ChartSpec, status: undefined, stages: addStage(m.stages, "Choose visualization", "complete") })); }
          if (name === "diagram") { receivedResponse = true; update(m => ({ ...m, diagram: data.mermaid, status: undefined, stages: completeStages(m.stages) })); }
          if (name === "suggestions") { receivedResponse = true; update(m => ({ ...m, actions: Array.isArray(data.actions) ? data.actions as ChatAction[] : m.actions })); }
          if (name === "error") { receivedResponse = true; update(m => ({ ...m, text: m.text ? `${m.text}\n\n${data.message}` : data.message, status: undefined })); }
        }
      }
      if (!receivedResponse) update(m => ({ ...m, text: "The server finished without a response. Check that the backend is running, then try again.", status: undefined }));
    } catch (error) {
      setMessages(all => all.map((m, i) => i === all.length - 1 ? { ...m, text: error instanceof Error ? error.message : "Connection failed.", status: undefined } : m));
    } finally { setBusy(false); }
  }, [sessionId, providerConfig]);

  return { messages, busy, send };
}
