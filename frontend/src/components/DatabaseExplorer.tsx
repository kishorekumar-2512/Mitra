import { Search, Table2, KeyRound, Link2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ResultsTable } from "./ResultsTable";
import type { QueryTable } from "../lib/types";

interface Column { name: string; type: string; nullable?: boolean; primary_key?: boolean; }
interface ForeignKey { column: string; references_table: string; references_column: string; }
interface TableInfo { name: string; columns: Column[]; foreign_keys: ForeignKey[]; count?: number; }

export function DatabaseExplorer() {
  const [tables, setTables] = useState<TableInfo[]>([]);
  const [selected, setSelected] = useState("");
  const [filter, setFilter] = useState("");
  const [preview, setPreview] = useState<QueryTable | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetch("/api/schema").then(r => r.json()), fetch("/api/stats").then(r => r.json())]).then(([schema, stats]) => {
      const enhanced = (schema.tables || []).map((table: TableInfo) => ({ ...table, count: stats.tables?.[table.name] || 0 }));
      setTables(enhanced); setSelected(enhanced[0]?.name || ""); setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (selected) fetch(`/api/tables/${selected}/rows?limit=50`).then(r => r.json()).then(data => setPreview(data.error ? null : data)).catch(() => setPreview(null));
  }, [selected]);

  const visible = useMemo(() => tables.filter(table => `${table.name} ${table.columns.map(column => column.name).join(" ")}`.toLowerCase().includes(filter.toLowerCase())), [tables, filter]);
  const table = tables.find(item => item.name === selected);
  const typeClass = (type: string) => type.toLowerCase().includes("int") ? "type-int" : type.toLowerCase().match(/char|text|varchar/) ? "type-text" : type.toLowerCase().match(/float|real|double/) ? "type-real" : type.toLowerCase().match(/date|time/) ? "type-date" : "";

  if (loading) return <div className="database-explorer database-mode"><div className="energy-ring" style={{ margin: "60px auto" }} /></div>;

  return (
    <div className="database-explorer database-mode">
      <header className="workspace-header">
        <div>
          <span className="eyebrow">DATABASE EXPLORER</span>
          <h1>Browse your data</h1>
          <p>Search tables and columns, inspect relationships, and preview the latest 50 rows.</p>
        </div>
        <div className="database-summary"><Table2 size={18} /> {tables.length} tables</div>
      </header>
      <div className="database-workspace">
        <aside className="table-sidebar">
          <label className="table-search"><Search size={16} /><input value={filter} onChange={event => setFilter(event.target.value)} placeholder="Search tables or fields" /></label>
          <div className="table-list">
            {visible.map(item => <button className={item.name === selected ? "selected" : ""} onClick={() => setSelected(item.name)} key={item.name}><Table2 size={16} /><span>{item.name}</span><small>{item.count}</small></button>)}
          </div>
        </aside>
        <section className="table-detail">
          {table ? <>
            <div className="table-title"><div><span className="table-icon"><Table2 size={18} /></span><h2>{table.name}</h2></div><span className="row-badge">{table.count} total rows</span></div>
            <div className="column-list">
              <h3>Columns</h3>
              {table.columns.map(column => <div className="column-row" key={column.name}><span>{column.primary_key ? <KeyRound size={14} /> : null}{column.name}</span><code className={typeClass(column.type)}>{column.type}</code><small>{column.nullable ? "nullable" : "required"}</small></div>)}
            </div>
            {table.foreign_keys.length > 0 && <div className="relationships"><h3>Relationships</h3>{table.foreign_keys.map(fk => <span key={fk.column}><Link2 size={14} />{fk.column} → {fk.references_table}.{fk.references_column}</span>)}</div>}
            <div className="preview-section">
              <div className="preview-heading"><h3>Data preview</h3><span>First 50 rows</span></div>
              {preview ? <ResultsTable table={preview} /> : <p className="muted">No rows available for this table.</p>}
            </div>
          </> : <p className="muted">Select a table to inspect it.</p>}
        </section>
      </div>
    </div>
  );
}
