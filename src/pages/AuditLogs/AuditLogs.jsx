import { useState, useEffect, useCallback } from "react";
import { Search, Filter, RefreshCw, Loader2 } from "lucide-react";
import { C, FONT_MONO } from "../../constants/theme";
import { Panel } from "../../components/common/Panel";
import { DataTable } from "../../components/tables/DataTable";
import { StatusChip } from "../../components/common/StatusChip";
import { auditService } from "../../services/auditService";

export function AuditLogsPage() {
  const [logs, setLogs] = useState([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [loading, setLoading] = useState(true);

  const fetchLogs = useCallback(async () => {
    try {
      const data = await auditService.getAuditLogs({
        search: search.trim() || undefined,
        status: statusFilter !== "all" ? statusFilter : undefined,
        limit: 150,
      });
      setLogs(data.logs || []);
    } catch (err) {
      console.warn("Error loading audit logs:", err);
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter]);

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 4000);
    return () => clearInterval(interval);
  }, [fetchLogs]);

  return (
    <div className="p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold" style={{ color: C.textPrimary }}>Audit Logs</h2>
          <p className="text-sm mt-0.5" style={{ color: C.textTertiary }}>
            {logs.length} event(s) recorded across platform operations
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div
            className="flex items-center gap-2 px-3 h-9 rounded-lg"
            style={{ background: C.surface2, border: `1px solid ${C.border}`, width: 240 }}
          >
            <Search size={13} style={{ color: C.textTertiary }} />
            <input
              type="text"
              placeholder="Filter logs…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-transparent border-none outline-none text-[13px] w-full"
              style={{ color: C.textPrimary }}
            />
          </div>
          <button
            onClick={fetchLogs}
            className="flex items-center gap-1.5 px-3 h-9 rounded-lg text-xs font-medium cursor-pointer"
            style={{ background: C.surface2, border: `1px solid ${C.border}`, color: C.textSecondary }}
          >
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      <div className="flex gap-2">
        {["all", "Success", "Failed", "Escalated"].map((st) => (
          <button
            key={st}
            onClick={() => setStatusFilter(st)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium cursor-pointer"
            style={{
              background: statusFilter === st ? C.accentSoft : C.surface2,
              color: statusFilter === st ? C.accent : C.textSecondary,
              border: `1px solid ${statusFilter === st ? C.accentBorder : C.border}`,
            }}
          >
            <Filter size={11} /> {st}
          </button>
        ))}
      </div>

      <Panel pad={false}>
        {logs.length === 0 ? (
          <div
            className="p-12 text-center text-sm"
            style={{ color: C.textTertiary }}
          >
            {loading ? (
              <div className="flex items-center justify-center gap-2">
                <Loader2 size={16} className="animate-spin" /> Loading audit logs...
              </div>
            ) : (
              "No audit events recorded matching current filters."
            )}
          </div>
        ) : (
          <DataTable
            columns={["Timestamp", "Action", "Performed By", "Target", "Cluster", "Duration", "Status"]}
            rows={logs}
            renderRow={(l, i) => (
              <tr
                key={l.id || i}
                style={{ borderBottom: i === logs.length - 1 ? "none" : `1px solid ${C.borderSoft}` }}
              >
                <td className="px-3 py-3 text-[13px]" style={{ color: C.textTertiary, fontFamily: FONT_MONO }}>
                  {l.ts}
                </td>
                <td className="px-3 py-3 text-[13px]" style={{ color: C.textPrimary }}>
                  {l.action}
                </td>
                <td className="px-3 py-3 text-[13px]" style={{ color: C.textSecondary }}>
                  {l.performed_by || l.by}
                </td>
                <td className="px-3 py-3 text-[13px]" style={{ color: C.textSecondary, fontFamily: FONT_MONO }}>
                  {l.target}
                </td>
                <td className="px-3 py-3 text-[13px]" style={{ color: C.textTertiary, fontFamily: FONT_MONO }}>
                  {l.cluster}
                </td>
                <td className="px-3 py-3 text-[13px]" style={{ color: C.textTertiary, fontFamily: FONT_MONO }}>
                  {l.duration}
                </td>
                <td className="px-3 py-3">
                  <StatusChip status={l.status} />
                </td>
              </tr>
            )}
          />
        )}
      </Panel>
    </div>
  );
}

export default AuditLogsPage;
