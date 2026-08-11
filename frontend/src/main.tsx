import { useState, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { ChartNoAxesCombined, Database, MessageSquare, Zap } from "lucide-react";
import { ChatWindow } from "./components/ChatWindow";
import { Dashboard } from "./components/Dashboard";
import { DatabaseExplorer } from "./components/DatabaseExplorer";
import { ParticleBackground } from "./components/ParticleBackground";
import "./styles.css";

const sessionId = localStorage.getItem("mitra-session") || crypto.randomUUID();
localStorage.setItem("mitra-session", sessionId);

function App() {
  const [page, setPage] = useState<"chat" | "dashboard" | "database">("chat");

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      document.body.style.setProperty("--mx", `${e.clientX}px`);
      document.body.style.setProperty("--my", `${e.clientY}px`);
    };
    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  return (
    <>
      <ParticleBackground />
      <div className="app">
        <aside>
          <div className="brand">
            <div className="brand-orb"></div>
            <span className="brand-text">MITRA</span>
          </div>
          <nav>
            <button className={page === "chat" ? "active" : ""} onClick={() => setPage("chat")}>
              <MessageSquare size={18} /> Chat
            </button>
            <button className={page === "database" ? "active" : ""} onClick={() => setPage("database")}>
              <Database size={18} /> Database
            </button>
            <button className={page === "dashboard" ? "active" : ""} onClick={() => setPage("dashboard")}>
              <ChartNoAxesCombined size={18} /> Dashboard
            </button>
          </nav>
          <div className="sessions">
            <small>THIS SESSION</small>
            <button className="session active">
              <span /> Demo workspace
            </button>
          </div>
          <footer>
            <Zap size={16} /> Neural Link Active
          </footer>
        </aside>
        {page === "chat" ? (
          <ChatWindow sessionId={sessionId} />
        ) : page === "database" ? (
          <DatabaseExplorer />
        ) : (
          <Dashboard sessionId={sessionId} onOpenChat={() => setPage("chat")} />
        )}
      </div>
    </>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
