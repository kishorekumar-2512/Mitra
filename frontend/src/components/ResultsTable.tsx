import type { QueryTable } from "../lib/types";

function cell(value: unknown) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value);
  return String(value);
}

export function ResultsTable({ table }: { table: QueryTable }) {
  if (!table.columns?.length) return null;
  return (
    <section className="results-table-wrap">
      <div className="result-table-heading">
        <strong>Query results</strong>
        <span>{table.row_count} row{table.row_count === 1 ? "" : "s"}{table.truncated ? " (truncated)" : ""}</span>
      </div>
      <div className="result-table-scroll">
        <table className="results-table">
          <thead><tr>{table.columns.map(column => <th key={column}>{column.replaceAll("_", " ")}</th>)}</tr></thead>
          <tbody>{table.rows.map((row, index) => <tr key={index}>{table.columns.map(column => <td key={column}>{cell(row[column])}</td>)}</tr>)}</tbody>
        </table>
      </div>
    </section>
  );
}
