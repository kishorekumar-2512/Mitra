import { useRef } from "react";
import { BarChart, Bar, CartesianGrid, Cell, LineChart, Line, PieChart, Pie, ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import type { ChartSpec } from "../lib/types";
import { downloadPng, exportCsv } from "../lib/export";

const COLORS = ["#4f46e5", "#06b6d4", "#10b981", "#f59e0b", "#f43f5e", "#8b5cf6", "#ec4899", "#14b8a6"];

export function ChartRenderer({ chart, onPin }: { chart: ChartSpec; onPin?: (chart: ChartSpec) => void }) {
  const ref = useRef<HTMLDivElement>(null); 
  const shortLabel = (value: unknown) => {
    const label = String(value ?? "");
    return label.length > 18 ? `${label.slice(0, 16)}…` : label;
  };
  const common = (
    <>
      <CartesianGrid stroke="#203858" strokeDasharray="3 3"/>
      <XAxis dataKey={chart.x_field} stroke="#7f9cc4" tickLine={false} tick={{ fontSize: 12 }} tickFormatter={shortLabel} interval="preserveStartEnd" height={54}/>
      <YAxis stroke="#7f9cc4" tickLine={false} tick={{ fontSize: 12 }} width={54}/>
      <Tooltip 
        contentStyle={{ background: '#08142a', border: '1px solid #1b426a', borderRadius: '8px', color: '#e0f0ff' }}
        itemStyle={{ color: '#e0f0ff' }}
        labelStyle={{ color: '#8aa4c8' }}
      />
    </>
  );
  
  const body = chart.type === "bar" ? (
    <BarChart data={chart.data}>{common}<Bar dataKey={chart.y_field} radius={[6,6,0,0]}>{chart.data.map((_, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}</Bar></BarChart>
  ) : chart.type === "line" ? (
    <LineChart data={chart.data}>{common}<Line type="monotone" dataKey={chart.y_field} stroke={COLORS[0]} strokeWidth={3} dot={{ fill: COLORS[3], stroke: "#fff", strokeWidth: 2, r: 4 }} activeDot={{ r: 6, fill: COLORS[4] }}/></LineChart>
  ) : chart.type === "scatter" ? (
    <ScatterChart>{common}<Scatter data={chart.data}>{chart.data.map((_, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}</Scatter></ScatterChart>
  ) : (
    <PieChart><Tooltip contentStyle={{ background: '#08142a', border: '1px solid #1b426a', borderRadius: '8px', color: '#e0f0ff' }} itemStyle={{ color: '#e0f0ff' }} labelStyle={{ color: '#8aa4c8' }}/><Pie data={chart.data} dataKey={chart.y_field} nameKey={chart.x_field} label={false}>{chart.data.map((_, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}</Pie></PieChart>
  );
  const showColorKey = (chart.type === "bar" || chart.type === "pie") && chart.data.length > 1;
  
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
        <ResponsiveContainer width="100%" height="100%">{body}</ResponsiveContainer>
      </div>
      {showColorKey && <div className="chart-color-key" aria-label="Chart category colors">
        {chart.data.map((row, index) => <span key={String(row[chart.x_field])} title={String(row[chart.x_field])}><i style={{ background: COLORS[index % COLORS.length] }} />{String(row[chart.x_field])}</span>)}
      </div>}
    </section>
  );
}
