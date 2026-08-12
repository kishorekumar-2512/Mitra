import { DragEvent, useEffect, useState } from "react";
import type { ChartSpec } from "../lib/types";
import { ChartRenderer } from "./ChartRenderer";

export function Dashboard({ sessionId, onOpenChat }: { sessionId: string; onOpenChat: () => void }) {
  const [pins, setPins] = useState<ChartSpec[]>([]);
  const [library, setLibrary] = useState<ChartSpec[]>([]);
  const [dragging, setDragging] = useState<number | null>(null);

  useEffect(() => {
    fetch(`/api/sessions/${sessionId}`).then(r => r.json()).then(data => { if (Array.isArray(data?.pinned)) setPins(data.pinned); }).catch(() => {});
    fetch("/api/analytics").then(r => r.json()).then(data => { if (Array.isArray(data?.charts)) setLibrary(data.charts); }).catch(() => {});
  }, [sessionId]);

  const reorder = async (target: number) => {
    if (dragging === null || dragging === target) return;
    const next = [...pins]; const [moved] = next.splice(dragging, 1); next.splice(target, 0, moved);
    setPins(next); setDragging(null);
    await fetch(`/api/sessions/${sessionId}/pins`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(next) });
  };
  const pin = async (chart: ChartSpec) => {
    if (pins.some(item => item.title === chart.title)) return;
    const next = [...pins, chart]; setPins(next);
    await fetch(`/api/sessions/${sessionId}/pins`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ chart }) });
  };

  return (
    <div className="dashboard">
      <header className="workspace-header">
        <div><span className="eyebrow">ANALYTICS LIBRARY</span><h1>Data overview</h1><p>14 live visualizations generated from your database. Pin the views you use most.</p></div>
        <button className="outline-action" onClick={onOpenChat}>Ask a custom question</button>
      </header>
      {pins.length > 0 && <section className="dashboard-section"><h2>Saved views</h2><div className="analytics-grid saved-grid">{pins.map((chart, i) => <div key={`${chart.title}-${i}`} className="draggable-chart" draggable onDragStart={() => setDragging(i)} onDragOver={(event: DragEvent) => event.preventDefault()} onDrop={() => reorder(i)}><ChartRenderer chart={chart} /></div>)}</div></section>}
      <section className="dashboard-section"><h2>Recommended analytics <span>{library.length} charts</span></h2><div className="analytics-grid">{library.map(chart => <ChartRenderer key={chart.title} chart={chart} onPin={pin} />)}</div></section>
    </div>
  );
}
