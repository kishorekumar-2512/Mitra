import { useCallback, useState } from "react";
import type { ChatMessage, ChartSpec } from "../lib/types";

const api = import.meta.env.VITE_API_URL || "";
export type Provider = "anthropic" | "groq" | "gemini";
export interface ProviderConfig { provider: Provider; apiKey: string; model: string; }
export function useChatStream(sessionId: string, providerConfig: ProviderConfig) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const send = useCallback(async (message: string) => {
    setMessages(current => [...current, { id: crypto.randomUUID(), role: "user", text: message }, { id: crypto.randomUUID(), role: "assistant", text: "", status: "Thinking…" }]);
    setBusy(true);
    try {
      const response = await fetch(`${api}/api/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: sessionId, message, provider: providerConfig.provider, api_key: providerConfig.apiKey || undefined, model: providerConfig.model || undefined }) });
      if (!response.ok || !response.body) throw new Error("Could not start the analysis stream.");
      const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = "";
      const update = (fn: (current: ChatMessage) => ChatMessage) => setMessages(all => all.map((item, i) => i === all.length - 1 ? fn(item) : item));
      while (true) {
        const result = await reader.read(); if (result.done) break; buffer += decoder.decode(result.value, { stream: true });
        const blocks = buffer.split("\n\n"); buffer = blocks.pop() || "";
        for (const block of blocks) { const name = block.match(/^event: (.+)$/m)?.[1]; const raw = block.match(/^data: (.+)$/m)?.[1]; if (!name || !raw) continue; const data = JSON.parse(raw);
          if (name === "token") update(m => ({ ...m, text: m.text + data.text, status: undefined }));
          if (name === "tool_call") update(m => ({ ...m, status: ({ get_schema: "Inspecting database…", execute_query: "Running SQL query…", generate_chart: "Building chart…", generate_flowchart: "Drawing diagram…", explain_data: "Explaining findings…" } as Record<string, string>)[data.name] || "Working…" }));
          if (name === "sql") update(m => ({ ...m, sql: data.sql }));
          if (name === "chart") update(m => ({ ...m, chart: data as ChartSpec, status: undefined }));
          if (name === "diagram") update(m => ({ ...m, diagram: data.mermaid, status: undefined }));
          if (name === "error") update(m => ({ ...m, text: data.message, status: undefined }));
        }
      }
    } catch (error) { setMessages(all => all.map((m, i) => i === all.length - 1 ? { ...m, text: error instanceof Error ? error.message : "Connection failed.", status: undefined } : m)); }
    finally { setBusy(false); }
  }, [sessionId, providerConfig]);
  return { messages, busy, send };
}
