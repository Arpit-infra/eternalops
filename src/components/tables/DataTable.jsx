import { C } from "../../constants/theme";

export function DataTable({ columns, rows, renderRow }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr style={{ borderBottom: `1px solid ${C.border}` }}>
            {columns.map((c) => (
              <th key={c} className="text-left px-3 py-2.5 text-xs font-medium uppercase tracking-wide" style={{ color: C.textTertiary }}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => renderRow(row, i))}
        </tbody>
      </table>
    </div>
  );
}
