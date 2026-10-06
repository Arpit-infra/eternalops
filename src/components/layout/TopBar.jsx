import { useState, useEffect, useCallback, useRef } from "react";
import { Search, ChevronDown, Globe2, Bell, Check, AlertOctagon, HeartPulse, ShieldAlert, Info, Server } from "lucide-react";
import { C, FONT_MONO } from "../../constants/theme";
import { IconButton } from "../common/IconButton";
import { notificationService } from "../../services/notificationService";
import { environmentService } from "../../services/environmentService";

export function TopBar({ pageTitle }) {
  const [environments, setEnvironments] = useState([]);
  const [selectedEnv, setSelectedEnv] = useState(null);
  const [showEnvDropdown, setShowEnvDropdown] = useState(false);
  const [showNotifs, setShowNotifs] = useState(false);
  const [notifData, setNotifData] = useState({ total: 0, unread_count: 0, notifications: [] });
  const notifRef = useRef(null);
  const envRef = useRef(null);

  const fetchEnvironments = useCallback(async () => {
    try {
      const envs = await environmentService.getEnvironments();
      setEnvironments(envs);
      if (envs.length > 0 && !selectedEnv) {
        setSelectedEnv(envs[0]);
      }
    } catch (err) {
      // ignore
    }
  }, [selectedEnv]);

  const fetchNotifs = useCallback(async () => {
    try {
      const data = await notificationService.getNotifications();
      setNotifData(data);
    } catch (err) {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchEnvironments();
    fetchNotifs();
    const interval = setInterval(() => {
      fetchNotifs();
      fetchEnvironments();
    }, 5000);
    return () => clearInterval(interval);
  }, [fetchEnvironments, fetchNotifs]);

  // Click outside to close dropdown
  useEffect(() => {
    function handleClickOutside(event) {
      if (notifRef.current && !notifRef.current.contains(event.target)) {
        setShowNotifs(false);
      }
      if (envRef.current && !envRef.current.contains(event.target)) {
        setShowEnvDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleMarkAllRead = async () => {
    await notificationService.markAllRead();
    await fetchNotifs();
  };

  const handleMarkRead = async (id) => {
    await notificationService.markRead(id);
    await fetchNotifs();
  };

  const getNotifIcon = (type) => {
    switch (type) {
      case "critical":
        return <ShieldAlert size={13} style={{ color: C.critical }} />;
      case "escalate":
        return <AlertOctagon size={13} style={{ color: C.critical }} />;
      case "heal":
        return <HeartPulse size={13} style={{ color: C.accent }} />;
      case "success":
        return <Check size={13} style={{ color: C.success }} />;
      default:
        return <Info size={13} style={{ color: C.info }} />;
    }
  };

  return (
    <header
      className="flex items-center justify-between h-16 px-6 shrink-0"
      style={{ borderBottom: `1px solid ${C.border}`, background: C.bg }}
    >
      <div className="flex items-center gap-4 min-w-0">
        <h1 className="text-[15px] font-semibold" style={{ color: C.textPrimary }}>{pageTitle}</h1>
      </div>
      <div className="flex items-center gap-2">
        <div
          className="hidden md:flex items-center gap-2 px-3 h-9 rounded-lg"
          style={{ background: C.surface2, border: `1px solid ${C.border}`, width: 260 }}
        >
          <Search size={14} style={{ color: C.textTertiary }} />
          <span className="text-[13px]" style={{ color: C.textTertiary }}>Search services, pods, incidents…</span>
          <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded" style={{ color: C.textTertiary, background: C.surface3, fontFamily: FONT_MONO }}>⌘K</span>
        </div>

        {/* Dynamic Control Plane Environment Selector */}
        <div className="relative" ref={envRef}>
          <button
            onClick={() => setShowEnvDropdown(!showEnvDropdown)}
            className="flex items-center gap-2 px-3 h-9 rounded-lg text-[13px] font-medium cursor-pointer transition-colors"
            style={{ background: C.surface2, border: `1px solid ${C.border}`, color: C.textPrimary }}
          >
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: 999,
                background: selectedEnv?.status === "CONNECTED" ? C.success : C.critical,
              }}
              className={selectedEnv?.status === "CONNECTED" ? "animate-pulse" : ""}
            />
            <span className="font-semibold">{selectedEnv?.name || "Local Development"}</span>
            <span className="text-[11px] px-1.5 py-0.5 rounded" style={{ background: C.surface3, color: C.textTertiary, fontFamily: FONT_MONO }}>
              {selectedEnv?.provider || "docker-desktop"}
            </span>
            <ChevronDown size={13} style={{ color: C.textTertiary }} />
          </button>

          {showEnvDropdown && (
            <div
              className="absolute right-0 mt-2 w-72 rounded-xl shadow-2xl z-50 overflow-hidden flex flex-col p-2"
              style={{ background: C.bgElevated, border: `1px solid ${C.border}` }}
            >
              <div className="px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wider" style={{ color: C.textTertiary }}>
                Active Environments
              </div>
              {environments.map((e) => (
                <button
                  key={e.id}
                  onClick={() => {
                    setSelectedEnv(e);
                    setShowEnvDropdown(false);
                  }}
                  className="flex items-center justify-between p-2 rounded-lg text-left hover:bg-white/5 transition-colors cursor-pointer w-full"
                  style={{
                    background: selectedEnv?.id === e.id ? `${C.accentSoft}50` : "transparent",
                  }}
                >
                  <div className="flex items-center gap-2">
                    <span
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: 999,
                        background: e.status === "CONNECTED" ? C.success : C.critical,
                      }}
                    />
                    <div>
                      <div className="text-[12px] font-medium" style={{ color: C.textPrimary }}>
                        {e.name}
                      </div>
                      <div className="text-[10px]" style={{ color: C.textTertiary, fontFamily: FONT_MONO }}>
                        {e.platform} · {e.connection_type}
                      </div>
                    </div>
                  </div>
                  {selectedEnv?.id === e.id && <Check size={14} style={{ color: C.accent }} />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Notifications Area */}
        <div className="relative" ref={notifRef}>
          <IconButton icon={Bell} onClick={() => setShowNotifs(!showNotifs)} />
          {notifData.unread_count > 0 && (
            <span
              style={{
                position: "absolute",
                top: 4,
                right: 4,
                minWidth: 14,
                height: 14,
                borderRadius: 999,
                background: C.critical,
                border: `1.5px solid ${C.bg}`,
                color: "#fff",
                fontSize: 9,
                fontWeight: 700,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: "0 2px",
              }}
            >
              {notifData.unread_count}
            </span>
          )}

          {/* Notifications Dropdown */}
          {showNotifs && (
            <div
              className="absolute right-0 mt-2 w-80 rounded-2xl shadow-2xl z-50 overflow-hidden flex flex-col"
              style={{ background: C.bgElevated, border: `1px solid ${C.border}`, maxHeight: 420 }}
            >
              <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: C.border }}>
                <span className="text-xs font-semibold" style={{ color: C.textPrimary }}>Notifications</span>
                {notifData.unread_count > 0 && (
                  <button
                    onClick={handleMarkAllRead}
                    className="text-[11px] hover:underline cursor-pointer"
                    style={{ color: C.accent }}
                  >
                    Mark all read
                  </button>
                )}
              </div>
              <div className="overflow-y-auto flex-1 divide-y" style={{ borderColor: C.borderSoft }}>
                {notifData.notifications.length === 0 ? (
                  <div className="p-6 text-center text-xs" style={{ color: C.textTertiary }}>
                    No notifications
                  </div>
                ) : (
                  notifData.notifications.map((n) => (
                    <div
                      key={n.id}
                      onClick={() => handleMarkRead(n.id)}
                      className="p-3 flex items-start gap-2.5 hover:bg-white/5 transition-colors cursor-pointer"
                      style={{ background: n.read ? "transparent" : `${C.accentSoft}40` }}
                    >
                      <div className="mt-0.5 shrink-0">{getNotifIcon(n.type)}</div>
                      <div className="min-w-0 flex-1">
                        <div className="text-[12px] font-medium leading-snug" style={{ color: C.textPrimary }}>
                          {n.title}
                        </div>
                        <div className="text-[11px] mt-0.5 leading-snug" style={{ color: C.textSecondary }}>
                          {n.message}
                        </div>
                        <div className="text-[10px] mt-1" style={{ color: C.textTertiary, fontFamily: FONT_MONO }}>
                          {n.time_str}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        <div className="w-px h-6 mx-1" style={{ background: C.border }} />

        <div className="flex items-center gap-2 pl-1 pr-2 py-1 rounded-lg" style={{ cursor: "pointer" }}>
          <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold" style={{ background: C.violetSoft, color: C.violet }}>NK</div>
        </div>
      </div>
    </header>
  );
}
