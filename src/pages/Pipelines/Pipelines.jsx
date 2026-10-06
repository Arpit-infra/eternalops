import { GitBranch, GitCommit, RotateCcw, RefreshCw, MoreHorizontal } from "lucide-react";
import { C, FONT_MONO } from "../../constants/theme";
import { Panel } from "../../components/common/Panel";
import { DataTable } from "../../components/tables/DataTable";
import { StatusChip } from "../../components/common/StatusChip";
import { IconButton } from "../../components/common/IconButton";
import { pipelines } from "../../data/dashboardData";

export function CicdPage() {
  return (
    <div className="p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold" style={{ color: C.textPrimary }}>CI/CD Pipelines</h2>
          <p className="text-sm mt-0.5" style={{ color: C.textTertiary }}>8 pipelines · 99.2% success rate over 7 days</p>
        </div>
        <div className="flex gap-3">
          <div className="rounded-xl px-4 py-2.5 text-center" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
            <div className="text-[15px] font-semibold" style={{ fontFamily: FONT_MONO, color: C.success }}>99.2%</div>
            <div className="text-[10px]" style={{ color: C.textTertiary }}>Success rate</div>
          </div>
          <div className="rounded-xl px-4 py-2.5 text-center" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
            <div className="text-[15px] font-semibold" style={{ fontFamily: FONT_MONO, color: C.textPrimary }}>2m 41s</div>
            <div className="text-[10px]" style={{ color: C.textTertiary }}>Avg duration</div>
          </div>
        </div>
      </div>

      <Panel pad={false}>
        <DataTable
          columns={["Pipeline", "Branch", "Commit", "Author", "Status", "Duration", "Actions"]}
          rows={pipelines}
          renderRow={(p, i) => (
            <tr key={i} style={{ borderBottom: i === pipelines.length - 1 ? "none" : `1px solid ${C.borderSoft}` }}>
              <td className="px-3 py-3 text-[13px] font-medium" style={{ color: C.textPrimary }}>{p.name}</td>
              <td className="px-3 py-3 text-[13px] flex items-center gap-1.5" style={{ color: C.textSecondary }}><GitBranch size={12} style={{ color: C.textTertiary }} />{p.branch}</td>
              <td className="px-3 py-3 text-[13px]" style={{ color: C.textSecondary, fontFamily: FONT_MONO }}><span className="flex items-center gap-1.5"><GitCommit size={12} style={{ color: C.textTertiary }} />{p.commit}</span></td>
              <td className="px-3 py-3 text-[13px]" style={{ color: C.textSecondary }}>{p.author}</td>
              <td className="px-3 py-3"><StatusChip status={p.status} /></td>
              <td className="px-3 py-3 text-[13px]" style={{ color: C.textSecondary, fontFamily: FONT_MONO }}>{p.duration}</td>
              <td className="px-3 py-3">
                <div className="flex items-center gap-1">
                  <IconButton icon={RotateCcw} />
                  <IconButton icon={RefreshCw} />
                  <IconButton icon={MoreHorizontal} />
                </div>
              </td>
            </tr>
          )}
        />
      </Panel>
    </div>
  );
}

export default CicdPage;
