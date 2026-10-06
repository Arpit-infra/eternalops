import { C } from "../../constants/theme";

export function Panel({ title, subtitle, right, children, className = "", pad = true }) {
  return (
    <div
      className={`rounded-2xl ${className}`}
      style={{ background: C.surface, border: `1px solid ${C.border}` }}
    >
      {(title || right) && (
        <div className="flex items-center justify-between px-5 pt-5 pb-3">
          <div>
            {title && <h3 className="text-[13px] font-semibold tracking-wide" style={{ color: C.textPrimary }}>{title}</h3>}
            {subtitle && <p className="text-xs mt-0.5" style={{ color: C.textTertiary }}>{subtitle}</p>}
          </div>
          {right}
        </div>
      )}
      <div className={pad ? "px-5 pb-5" : ""}>{children}</div>
    </div>
  );
}
