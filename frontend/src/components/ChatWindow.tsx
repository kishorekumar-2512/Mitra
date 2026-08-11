import { FormEvent, useEffect, useRef, useState, MouseEvent } from "react";
import { Send, Settings, Trash2 } from "lucide-react";
import type { ChartSpec } from "../lib/types";
import { MessageBubble } from "./MessageBubble";
import { Provider, ProviderConfig, useChatStream } from "../hooks/useChatStream";

const defaults: Record<Provider, string> = { anthropic: "claude-sonnet-4-5-20250929", groq: "llama-3.1-8b-instant", gemini: "gemini-3.6-flash" };

interface SuggestionCategory { emoji: string; label: string; queries: string[]; }

export function ChatWindow({ sessionId }: { sessionId: string }) {
  const [provider, setProvider] = useState<Provider>("gemini");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState(defaults.gemini);
  const config: ProviderConfig = { provider, apiKey, model };
  const { messages, busy, send } = useChatStream(sessionId, config);
  const [value, setValue] = useState(""); 
  const end = useRef<HTMLDivElement>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [categories, setCategories] = useState<SuggestionCategory[]>([
    { emoji: "📊", label: "Sales & Revenue", queries: ["Show revenue by product as a bar chart", "Show monthly revenue trend as a line chart"] },
    { emoji: "🔗", label: "Diagrams", queries: ["Draw the database ER diagram"] },
  ]);

  useEffect(() => { void end.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);
  
  useEffect(() => {
    fetch("/api/providers").then(res => res.json()).then(data => {
      if (data && data.default_provider) {
        setProvider(data.default_provider as Provider);
        if (data.models && data.models[data.default_provider]) {
          setModel(data.models[data.default_provider]);
        } else {
          setModel(defaults[data.default_provider as Provider]);
        }
      }
    }).catch(() => {});

    fetch("/api/suggestions").then(res => res.json()).then(data => {
      if (data && data.categories) {
        setCategories(data.categories);
      }
    }).catch(() => {});
  }, []);

  const chooseProvider = (e: React.ChangeEvent<HTMLSelectElement>) => { 
    const next = e.target.value as Provider;
    setProvider(next); 
    setModel(defaults[next]); 
  };
  
  const submit = (event: FormEvent) => { event.preventDefault(); if (value.trim() && !busy) { send(value.trim()); setValue(""); } };
  const askStarter = (question: string) => { if (!busy) send(question); };

  return (
    <main className="chat">
      <div className="messages">
        {messages.length === 0 ? (
          <div className="hero">
            <div className="brand-orb" style={{ width: 64, height: 64 }}></div>
            <h1>How can I help you explore your data?</h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 24, maxWidth: 500, textAlign: 'center' }}>
              Ask questions about sales, customers, products, orders, employees, and more. I'll query the database, generate charts, and explain insights.
            </p>
            <div className="suggestions-grid">
              {categories.slice(0, 6).map((cat, ci) => (
                <div key={ci} className="suggestion-category">
                  <div className="suggestion-category-header">
                    <span>{cat.emoji}</span> {cat.label}
                  </div>
                  {cat.queries.slice(0, 2).map((q, qi) => (
                    <button key={qi} className="suggestion-pill" onClick={() => askStarter(q)} disabled={busy}>
                      {q}
                    </button>
                  ))}
                </div>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m) => <MessageBubble key={m.id} message={m} />)
        )}
        <div ref={end} />
      </div>

      <div className="input-area">
        {showSettings && (
          <div className="provider-settings">
            <select value={provider} onChange={chooseProvider}>
              <option value="anthropic">Anthropic</option>
              <option value="groq">Groq</option>
              <option value="gemini">Gemini</option>
            </select>
            <input placeholder="API Key (optional)" type="password" value={apiKey} onChange={e => setApiKey(e.target.value)} />
            <input placeholder="Model" value={model} onChange={e => setModel(e.target.value)} />
          </div>
        )}
        <form onSubmit={submit} className="input-box">
          <button type="button" onClick={() => setShowSettings(!showSettings)} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', paddingRight: '12px' }}>
            <Settings size={20} />
          </button>
          <input 
            value={value} 
            onChange={(e) => setValue(e.target.value)} 
            placeholder="Ask Mitra to analyze your data..." 
            disabled={busy} 
          />
          <button type="submit" className="send-btn" disabled={!value.trim() || busy}>
            <Send size={18} />
          </button>
        </form>
      </div>
    </main>
  );
}
