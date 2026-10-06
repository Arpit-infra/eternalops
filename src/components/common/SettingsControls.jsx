import { C } from "../../constants/theme";

export function Toggle({ on, onClick }) {
  return (
    <button
      onClick={onClick}
      className="w-9 h-5 rounded-full flex items-center px-0.5 transition-colors duration-150"
      style={{ background: on ? C.accent : C.surface3, justifyContent: on ? "flex-end" : "flex-start" }}
    >
      <span className="w-4 h-4 rounded-full bg-white block" />
    </button>
  );
}

export function SettingsRow({ label, desc, control }) {
  return (
    <div className="flex items-center justify-between py-3.5" style={{ borderBottom: `1px solid ${C.borderSoft}` }}>
      <div>
        <div className="text-[13px] font-medium" style={{ color: C.textPrimary }}>{label}</div>
        {desc && <div className="text-xs mt-0.5" style={{ color: C.textTertiary }}>{desc}</div>}
      </div>
      {control}
    </div>
  );
}
