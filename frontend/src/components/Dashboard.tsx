import { DragEvent, useEffect, useState } from "react";
import type { ChartSpec } from "../lib/types";
import { ChartRenderer } from "./ChartRenderer";

export function Dashboard({ sessionId, onOpenChat }: { sessionId: string; onOpenChat: () => void }) {
  const [pins, setPins] = useState<ChartSpec[]>([]);
  const [dragging, setDragging] = useState<number | null>(null);

  useEffect(() => {
    fetch(`/api/sessions/${sessionId}`)
      .then(r => r.json())
      .then(data => { if (data && Array.isArray(data.pinned)) setPins(data.pinned); })
      .catch(() => {});
  }, [sessionId]);

  const reorder = async (target: number) => {
    if (dragging === null || dragging === target) return;
    const next = [...pins];
    const [moved] = next.splice(dragging, 1);
    next.splice(target, 0, moved);
    setPins(next);
    setDragging(null);
    await fetch(`/api/sessions/${sessionId}/pins`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(next) });
  };

  const pin = async (chart: ChartSpec) => {
    await fetch(`/api/sessions/${sessionId}/pins`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ chart }) });
    setPins(prev => [...prev, chart]);
  };

  if (pins.length === 0) {
    return (
      <div className="dashboard">
        <div className="dashboard-empty">
          <div className="brand-orb" style={{ width: 80, height: 80, marginBottom: 24 }}></div>
          <h2>Dashboard is Empty</h2>
          <p>Ask Mitra to generate charts, then pin them to build your dashboard.</p>
          <button onClick={onOpenChat}>Open Chat</button>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div style={{ marginBottom: 32 }}>
        <span className="eyebrow">SAVED VIEWS</span>
        <h1 style={{ fontSize: "2rem", margin: "8px 0" }}>My Dashboard</h1>
        <p style={{ color: "var(--text-secondary)" }}>Pin charts from chat to build a reusable reporting view. Drag cards to reorder.</p>
      </div>
      <div style={{ display: "grid", gap: "24px", gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))" }}>
        {pins.map((chart, i) => (
          <div
            key={`${chart.title}-${i}`}
            className="draggable-chart"
            draggable
            onDragStart={() => setDragging(i)}
            onDragOver={(e: DragEvent) => e.preventDefault()}
            onDrop={() => reorder(i)}
          >
            <ChartRenderer chart={chart} onPin={pin} />
          </div>
        ))}
      </div>
    </div>
  );
}
