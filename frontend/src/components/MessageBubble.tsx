import { MouseEvent } from "react";
import type { ChatMessage } from "../lib/types";
import { ChartRenderer } from "./ChartRenderer";
import { MermaidRenderer } from "./MermaidRenderer";
import { SqlPanel } from "./SqlPanel";

export function MessageBubble({ message }: { message: ChatMessage }) {
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

  return (
    <div 
      className={`message ${message.role} tilt-card`}
      onMouseMove={handleTilt}
      onMouseLeave={handleLeave}
    >
      {message.status && (
        <div className="message-status">
          <div className="energy-ring" />
          <span>{message.status}</span>
        </div>
      )}
      {message.text && (
        <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{message.text}</div>
      )}
      {message.sql && <SqlPanel sql={message.sql} />}
      {message.chart && <ChartRenderer chart={message.chart} />}
      {message.diagram && <MermaidRenderer diagram={message.diagram} />}
    </div>
  );
}
