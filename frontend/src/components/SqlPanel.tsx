import { useState } from "react";
import { Copy, Check } from "lucide-react";

export function SqlPanel({ sql }: { sql: string }) {
  const [copied, setCopied] = useState(false);

  const copyCode = () => {
    navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const highlightSql = (text: string) => {
    const keywords = ["SELECT", "FROM", "WHERE", "JOIN", "ON", "GROUP BY", "ORDER BY", "DESC", "ASC", "LIMIT", "AS", "INNER", "LEFT", "RIGHT", "COUNT", "SUM", "AVG", "MIN", "MAX", "AND", "OR", "IN", "IS", "NULL"];
    let html = text;
    keywords.forEach(kw => {
      const regex = new RegExp(`\\b${kw}\\b`, 'gi');
      html = html.replace(regex, `<span class="sql-keyword">$&</span>`);
    });
    return html;
  };

  return (
    <div className="sql-panel">
      <button onClick={copyCode} title="Copy SQL">
        {copied ? <Check size={16} color="var(--accent-green)" /> : <Copy size={16} />}
      </button>
      <pre dangerouslySetInnerHTML={{ __html: highlightSql(sql) }} style={{ whiteSpace: "pre-wrap", margin: 0 }} />
    </div>
  );
}
