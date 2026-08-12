import { MouseEvent } from "react";
import { motion } from "framer-motion";
import type { ChatMessage } from "../lib/types";
import { ChartRenderer } from "./ChartRenderer";
import { MermaidRenderer } from "./MermaidRenderer";
import { SqlPanel } from "./SqlPanel";
import { ResultsTable } from "./ResultsTable";

const messageVariants = {
  hidden: { opacity: 0, y: 24, scale: 0.97, filter: "blur(6px)" },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    filter: "blur(0px)",
    transition: { type: "spring", stiffness: 260, damping: 28, mass: 0.8 },
  },
};

export function MessageBubble({ message, onAction }: { message: ChatMessage; onAction?: (prompt: string) => void }) {
  const handleTilt = (e: MouseEvent<HTMLDivElement>) => {
    const card = e.currentTarget;
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    const tiltX = (y - centerY) / 20;
    const tiltY = (centerX - x) / 20;
    card.style.setProperty("--tilt-x", `${tiltX}deg`);
    card.style.setProperty("--tilt-y", `${tiltY}deg`);
  };

  const handleLeave = (e: MouseEvent<HTMLDivElement>) => {
    const card = e.currentTarget;
    card.style.setProperty("--tilt-x", `0deg`);
    card.style.setProperty("--tilt-y", `0deg`);
  };

  const isThinking = message.role === "assistant" && !!message.status;

  return (
    <motion.div
      className={`message ${message.role} tilt-card${isThinking ? " thinking" : ""}`}
      variants={messageVariants}
      initial="hidden"
      animate="visible"
      onMouseMove={handleTilt}
      onMouseLeave={handleLeave}
    >
      {isThinking && <div className="scanline-overlay" />}
      {message.status && (
        <div className="message-status">
          <div className="energy-ring" />
          <span>{message.status}</span>
        </div>
      )}
      {message.stages && message.stages.length > 0 && (
        <div className="analysis-steps">
          {message.stages.map((stage, index) => <span key={`${stage.label}-${index}`} className={stage.state}><i />{stage.label}</span>)}
        </div>
      )}
      {message.text && (
        <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{message.text}</div>
      )}
      {message.actions && message.actions.length > 0 && <div className="message-actions">
        {message.actions.map(action => <button type="button" key={`${action.label}-${action.prompt}`} onClick={() => onAction?.(action.prompt)}>{action.label}</button>)}
      </div>}
      {message.sql && <SqlPanel sql={message.sql} />}
      {message.table && <ResultsTable table={message.table} />}
      {message.chart && <ChartRenderer chart={message.chart} />}
      {message.diagram && <MermaidRenderer diagram={message.diagram} />}
    </motion.div>
  );
}
