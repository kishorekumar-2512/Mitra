import { useEffect, useState } from "react";

interface Column { name: string; type: string; nullable?: boolean; primary_key?: boolean; }
interface ForeignKey { column: string; references_table: string; references_column: string; }
interface TableInfo { name: string; columns: Column[]; foreign_keys: ForeignKey[]; count?: number; }

export function DatabaseExplorer() {
  const [tables, setTables] = useState<TableInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch("/api/schema").then(r => r.json()).catch(() => ({ tables: [] })),
      fetch("/api/stats").then(r => r.json()).catch(() => ({ tables: {} }))
    ]).then(([schema, stats]) => {
      const schemaTables = schema.tables || [];
      const statCounts = stats.tables || {};
      const enhanced = schemaTables.map((t: any) => ({
        ...t,
        count: statCounts[t.name] || 0
      }));
      setTables(enhanced);
      setLoading(false);
    });
  }, []);

  const getTypeClass = (type: string) => {
    const t = type.toLowerCase();
    if (t.includes("int")) return "type-int";
    if (t.includes("char") || t.includes("text") || t.includes("varchar")) return "type-text";
    if (t.includes("real") || t.includes("float") || t.includes("double")) return "type-real";
    if (t.includes("date") || t.includes("time")) return "type-date";
    return "";
  };

  if (loading) return <div className="database-explorer"><div className="energy-ring" style={{ margin: "60px auto" }}></div></div>;

  return (
    <div className="database-explorer">
      <div style={{ marginBottom: 32 }}>
        <span className="eyebrow">LIVE DATABASE MAP</span>
        <h1 style={{ fontSize: "2rem", margin: "8px 0" }}>Your E-Commerce Database</h1>
        <p style={{ color: "var(--text-secondary)", maxWidth: 650, lineHeight: 1.6 }}>
          Mitra is connected to {tables.length} interconnected tables with rich e-commerce data including products, customers, orders, reviews, and employee records. Ask anything in chat.
        </p>
      </div>
      
      <div className="schema-grid">
        {tables.map(table => (
          <div key={table.name} className="schema-card">
            <h3>
              {table.name}
              {table.count !== undefined && <span className="badge">{table.count} rows</span>}
            </h3>
            <ul>
              {table.columns.map(col => (
                <li key={col.name}>
                  <span>{col.name} {col.primary_key ? <small style={{ color: "var(--accent-amber)" }}>PK</small> : ""}</span>
                  <span className={getTypeClass(col.type)}>{col.type}</span>
                </li>
              ))}
            </ul>
            {table.foreign_keys && table.foreign_keys.length > 0 && (
              <div style={{ marginTop: 12 }}>
                {table.foreign_keys.map((fk, i) => (
                  <div key={i} className="relation">
                    {fk.column} → {fk.references_table}.{fk.references_column}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
