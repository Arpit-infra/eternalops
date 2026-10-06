import { C } from "../../constants/theme";

export function IconButton({ icon: Icon, onClick, active }) {
  return (
    <button
      onClick={onClick}
      className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors duration-150"
      style={{ background: active ? C.surface3 : "transparent", color: active ? C.textPrimary : C.textSecondary }}
      onMouseEnter={(e) => { if (!active) e.currentTarget.style.background = C.surface2; }}
      onMouseLeave={(e) => { if (!active) e.currentTarget.style.background = "transparent"; }}
    >
      <Icon size={16} />
    </button>
  );
}
