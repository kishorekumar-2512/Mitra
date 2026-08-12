import React, { Suspense, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { ChartNoAxesCombined, Database, MessageSquare, Plus, Search, Zap } from "lucide-react";
import { ChatWindow } from "./components/ChatWindow";
import { Dashboard } from "./components/Dashboard";
import { DatabaseExplorer } from "./components/DatabaseExplorer";
import "./styles.css";

const ParticleBackground = React.lazy(() => import("./components/ParticleBackground"));

interface RecentChat { id: string; question: string; timestamp: number; }
const historyKey = "mitra-recent-chats";
const sevenDays = 7 * 24 * 60 * 60 * 1000;
const loadRecent = (): RecentChat[] => { try { return JSON.parse(localStorage.getItem(historyKey) || "[]").filter((item: RecentChat) => Date.now() - item.timestamp < sevenDays); } catch { return []; } };

function App() {
  const [page, setPage] = useState<"chat" | "dashboard" | "database">("chat");
  const [sessionId, setSessionId] = useState(() => localStorage.getItem("mitra-session") || crypto.randomUUID());
  const [recent, setRecent] = useState<RecentChat[]>(loadRecent);
  const [historySearch, setHistorySearch] = useState("");
  useEffect(() => { localStorage.setItem("mitra-session", sessionId); }, [sessionId]);
  useEffect(() => { localStorage.setItem(historyKey, JSON.stringify(recent)); }, [recent]);
  const visibleHistory = useMemo(() => recent.filter(item => item.question.toLowerCase().includes(historySearch.toLowerCase())), [recent, historySearch]);
  const recordQuestion = (question: string) => setRecent(current => [{ id: crypto.randomUUID(), question, timestamp: Date.now() }, ...current].slice(0, 30));
  const newChat = () => { setSessionId(crypto.randomUUID()); setPage("chat"); };
  const relativeTime = (timestamp: number) => { const hours = Math.floor((Date.now() - timestamp) / 3600000); return hours < 1 ? "Just now" : hours < 24 ? `${hours}h ago` : `${Math.floor(hours / 24)}d ago`; };

  return <>{page !== "database" && <Suspense fallback={null}><ParticleBackground /></Suspense>}<div className={`app ${page === "database" ? "database-app" : ""}`}>
    <aside><div className="brand"><div className="brand-orb" /><span className="brand-text">MITRA</span></div><button className="new-chat" onClick={newChat}><Plus size={18} />New chat</button>
      <nav><button className={page === "chat" ? "active" : ""} onClick={() => setPage("chat")}><MessageSquare size={18} />Chat</button><button className={page === "database" ? "active" : ""} onClick={() => setPage("database")}><Database size={18} />Database explorer</button><button className={page === "dashboard" ? "active" : ""} onClick={() => setPage("dashboard")}><ChartNoAxesCombined size={18} />Analytics dashboard</button></nav>
      <section className="conversation-history"><small>RECENT CONVERSATIONS</small><label><Search size={14} /><input value={historySearch} onChange={event => setHistorySearch(event.target.value)} placeholder="Search conversations" /></label><div>{visibleHistory.length ? visibleHistory.map(item => <button key={item.id} onClick={() => setPage("chat")} title={item.question}><span>{item.question}</span><small>{relativeTime(item.timestamp)}</small></button>) : <p>No chats in the last 7 days.</p>}</div></section>
      <footer><Zap size={16} /> SQL workspace ready</footer>
    </aside>
    {page === "chat" ? <ChatWindow key={sessionId} sessionId={sessionId} onAsk={recordQuestion} /> : page === "database" ? <DatabaseExplorer /> : <Dashboard sessionId={sessionId} onOpenChat={() => setPage("chat")} />}
  </div></>;
}

createRoot(document.getElementById("root")!).render(<App />);
