import { CSSProperties, FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { Mic, Send, Settings, Sparkles, Square } from "lucide-react";
import { MessageBubble } from "./MessageBubble";
import { JarvisOrb } from "./JarvisOrb";
import { TypingIndicator } from "./TypingIndicator";
import { Provider, ProviderConfig, useChatStream } from "../hooks/useChatStream";
import { useVoiceInput } from "../hooks/useVoiceInput";

const defaults: Record<Provider, string> = { anthropic: "claude-sonnet-4-5-20250929", groq: "llama-3.3-70b-versatile", gemini: "gemini-2.5-flash" };
interface SuggestionCategory { emoji: string; label: string; queries: string[]; }

export function ChatWindow({ sessionId, onAsk }: { sessionId: string; onAsk: (question: string) => void }) {
  const [provider, setProvider] = useState<Provider>("gemini");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState(defaults.gemini);
  const [providerModels, setProviderModels] = useState<Record<Provider, string>>(defaults);
  const { messages, busy, send } = useChatStream(sessionId, { provider, apiKey, model } as ProviderConfig);
  const [value, setValue] = useState(""); const end = useRef<HTMLDivElement>(null); const [showSettings, setShowSettings] = useState(false);
  const [categories, setCategories] = useState<SuggestionCategory[]>([]);

  useEffect(() => { void end.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);
  useEffect(() => {
    fetch("/api/providers").then(res => res.json()).then(data => { if (data?.models) setProviderModels(current => ({ ...current, ...data.models })); if (data?.default_provider) { const next = data.default_provider as Provider; setProvider(next); setModel(data.models?.[next] || defaults[next]); } }).catch(() => {});
    fetch("/api/suggestions").then(res => res.json()).then(data => { if (data?.categories) setCategories(data.categories); }).catch(() => {});
  }, []);

  const ask = (question: string) => { const trimmed = question.trim(); if (!trimmed || busy) return; onAsk(trimmed); void send(trimmed); setValue(""); };
  const { isListening, isTranscribing, audioLevel, hint: voiceHint, isSupported: voiceSupported, toggleListening } = useVoiceInput({
    value,
    onInterim: setValue,
    onFinal: transcript => {
      setValue(transcript);
      if (import.meta.env.VITE_VOICE_AUTO_SEND === "true") ask(transcript);
    },
  });
  const submit = (event: FormEvent) => { event.preventDefault(); ask(value); };
  const keyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); ask(value); } };
  const chooseProvider = (event: React.ChangeEvent<HTMLSelectElement>) => { const next = event.target.value as Provider; setProvider(next); setModel(providerModels[next] || defaults[next]); };

  const lastMsg = messages[messages.length - 1];
  const showTyping = busy && lastMsg?.role === "assistant" && !lastMsg.text;

  return <main className="chat">
    <header className="chat-header"><div><span className="eyebrow">SQL ANALYST</span><h1>Ask your data</h1></div><div style={{ display: "flex", alignItems: "center", gap: 16 }}><JarvisOrb active={busy} /><span className="connection"><i />Database connected</span></div></header>
    <div className="messages">
      {messages.length === 0 ? <div className="hero"><div className="hero-icon"><Sparkles size={28} /></div><h1>What would you like to analyze?</h1><p>Ask a question in plain language. Mitra will understand it, generate safe SQL, show results in a table, and create a chart when it helps.</p><div className="suggestions-grid">{categories.slice(0, 6).map(category => <div key={category.label} className="suggestion-category"><div className="suggestion-category-header"><span>{category.emoji}</span>{category.label}</div>{category.queries.slice(0, 2).map(question => <button key={question} className="suggestion-pill" onClick={() => ask(question)} disabled={busy}>{question}</button>)}</div>)}</div></div> : messages.map(message => <MessageBubble key={message.id} message={message} onAction={ask} />)}
      {showTyping && <TypingIndicator />}
      <div ref={end} />
    </div>
    <div className="input-area">
      {showSettings && <div className="provider-settings"><select value={provider} onChange={chooseProvider}><option value="anthropic">Anthropic</option><option value="groq">Groq</option><option value="gemini">Gemini</option></select><input placeholder="API Key (optional)" type="password" value={apiKey} onChange={event => setApiKey(event.target.value)} /><input placeholder="Model" value={model} onChange={event => setModel(event.target.value)} /></div>}
      <form onSubmit={submit} className="input-box">
        <textarea value={value} onChange={event => setValue(event.target.value)} onKeyDown={keyDown} placeholder="Ask anything about your database…" disabled={busy} rows={2} />
        <div className="input-footer"><button type="button" className="input-settings" onClick={() => setShowSettings(value => !value)} aria-label="Provider settings"><Settings size={17} /></button><span>{voiceHint || (isTranscribing ? "Transcribing your dictation…" : isListening ? "Listening… pause to finish" : <><kbd>Enter</kbd> send · <kbd>Shift</kbd> + <kbd>Enter</kbd> newline</>)}</span><button type="button" className={`voice-input-btn${isListening ? " is-listening" : ""}`} onClick={toggleListening} disabled={!voiceSupported || busy || isTranscribing} aria-label={isListening ? "Stop voice input" : "Start voice input"} title={!voiceSupported ? "Voice input not supported in this browser" : isListening ? "Stop listening" : "Use voice input"}>{isListening ? <Square size={15} fill="currentColor" /> : <Mic size={18} />}<i className="voice-waveform" aria-hidden="true" style={{ "--voice-level": Math.max(0.14, audioLevel).toFixed(2) } as CSSProperties}><b /><b /><b /><b /></i></button><button type="submit" className="send-btn" disabled={!value.trim() || busy} aria-label="Send question"><Send size={18} /></button></div>
      </form>
    </div>
  </main>;
}
