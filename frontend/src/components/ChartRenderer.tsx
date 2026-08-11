import { useRef } from "react";
import { BarChart, Bar, CartesianGrid, LineChart, Line, PieChart, Pie, ScatterChart, Scatter, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts";
import type { ChartSpec } from "../lib/types";
import { downloadPng, exportCsv } from "../lib/export";

const COLORS = ["#00d4ff", "#8c77ff", "#42d7b9", "#ff6b9d", "#ffb86b", "#60a5fa"];

export function ChartRenderer({ chart, onPin }: { chart: ChartSpec; onPin?: (chart: ChartSpec) => void }) {
  const ref = useRef<HTMLDivElement>(null); 
  const common = (
    <>
      <CartesianGrid stroke="var(--border-glass)" strokeDasharray="3 3"/>
      <XAxis dataKey={chart.x_field} stroke="var(--text-secondary)"/>
      <YAxis stroke="var(--text-secondary)"/>
      <Tooltip 
        contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-glass)', borderRadius: 'var(--radius-sm)' }} 
        itemStyle={{ color: 'var(--text-primary)' }}
      />
      <Legend />
    </>
  );
  
  const body = chart.type === "bar" ? (
    <BarChart data={chart.data}>{common}<Bar dataKey={chart.y_field} fill={COLORS[0]} radius={[5,5,0,0]}/></BarChart>
  ) : chart.type === "line" ? (
    <LineChart data={chart.data}>{common}<Line type="monotone" dataKey={chart.y_field} stroke={COLORS[1]} strokeWidth={3} dot={{ fill: COLORS[1], strokeWidth: 2, r: 4 }} activeDot={{ r: 6, stroke: 'var(--bg-void)' }}/></LineChart>
  ) : chart.type === "scatter" ? (
    <ScatterChart>{common}<Scatter data={chart.data} fill={COLORS[2]}/></ScatterChart>
  ) : (
    <PieChart><Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-glass)', borderRadius: 'var(--radius-sm)' }}/><Legend/><Pie data={chart.data} dataKey={chart.y_field} nameKey={chart.x_field} fill={COLORS[0]} label/></PieChart>
  );
  
  return (
    <section className="chart-card">
      <header>
        <h3>{chart.title}</h3>
        <span>
          {onPin && <button onClick={() => onPin(chart)}>Pin</button>}
          <button onClick={() => downloadPng(ref.current)}>PNG</button>
          <button onClick={() => exportCsv(chart.data)}>CSV</button>
        </span>
      </header>
      <div ref={ref} className="chart">
        <ResponsiveContainer width="100%" height={300}>{body}</ResponsiveContainer>
      </div>
    </section>
  );
}
