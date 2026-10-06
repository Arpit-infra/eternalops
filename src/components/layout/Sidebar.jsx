import { HeartPulse, ChevronRight, ChevronLeft } from "lucide-react";
import { C, FONT_MONO } from "../../constants/theme";
import { NAV_GROUPS } from "../../constants/navigation";

export function Sidebar({ active, onNavigate, collapsed, onToggle }) {
  return (
    <aside
      className="flex flex-col shrink-0 transition-all duration-200"
      style={{ width: collapsed ? 72 : 244, background: C.bgElevated, borderRight: `1px solid ${C.border}` }}
    >
      <div className="flex items-center gap-2.5 px-5 h-16 shrink-0" style={{ borderBottom: `1px solid ${C.borderSoft}` }}>
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 relative"
          style={{ background: `linear-gradient(135deg, ${C.accent}, #1a9d90)` }}
        >
          <HeartPulse size={16} color="#04201c" strokeWidth={2.5} />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <div className="text-[14px] font-semibold tracking-tight leading-none" style={{ color: C.textPrimary }}>EternalOps</div>
            <div className="text-[10px] mt-1" style={{ color: C.textTertiary, fontFamily: FONT_MONO }}>self-healing platform</div>
          </div>
        )}
      </div>

      <nav className="flex-1 overflow-y-auto py-4 px-3">
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="mb-5">
            {!collapsed && (
              <div className="px-2.5 mb-1.5 text-[10px] font-semibold uppercase tracking-wider" style={{ color: C.textTertiary }}>
                {group.label}
              </div>
            )}
            <div className="flex flex-col gap-0.5">
              {group.items.map((item) => {
                const isActive = active === item.id;
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={() => onNavigate(item.id)}
                    className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[13px] font-medium transition-all duration-150 relative"
                    style={{
                      background: isActive ? C.surface2 : "transparent",
                      color: isActive ? C.textPrimary : C.textSecondary,
                    }}
                    onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = C.surface; }}
                    onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = "transparent"; }}
                  >
                    {isActive && (
                      <span style={{ position: "absolute", left: -12, top: "50%", transform: "translateY(-50%)", width: 3, height: 16, borderRadius: 4, background: C.accent }} />
                    )}
                    <Icon size={16} style={{ color: isActive ? C.accent : C.textTertiary, flexShrink: 0 }} />
                    {!collapsed && <span className="truncate">{item.label}</span>}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="p-3" style={{ borderTop: `1px solid ${C.borderSoft}` }}>
        <button
          onClick={onToggle}
          className="w-full flex items-center justify-center gap-2 py-2 rounded-lg text-xs"
          style={{ color: C.textTertiary }}
        >
          {collapsed ? <ChevronRight size={14} /> : <><ChevronLeft size={14} /> Collapse</>}
        </button>
      </div>
    </aside>
  );
}
