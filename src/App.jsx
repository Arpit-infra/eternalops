import { useState } from "react";
import { C, FONT_SANS } from "./constants/theme";
import { PAGE_TITLES } from "./constants/navigation";
import { Sidebar } from "./components/layout/Sidebar";
import { TopBar } from "./components/layout/TopBar";
import { OverviewPage } from "./pages/Overview/Overview";
import { InfrastructurePage } from "./pages/Infrastructure/Infrastructure";
import { CicdPage } from "./pages/Pipelines/Pipelines";
import { KubernetesPage } from "./pages/Kubernetes/Kubernetes";
import { MonitoringPage } from "./pages/Monitoring/Monitoring";
import { IncidentsPage } from "./pages/Incidents/Incidents";
import { HealingEnginePage } from "./pages/HealingEngine/HealingEngine";
import { TopologyPage } from "./pages/Topology/Topology";
import { AuditLogsPage } from "./pages/AuditLogs/AuditLogs";
import { AICopilotPage } from "./pages/Copilot/Copilot";
import { SettingsPage } from "./pages/Settings/Settings";

export default function App() {
  const [page, setPage] = useState("overview");
  const [collapsed, setCollapsed] = useState(false);

  const renderPage = () => {
    switch (page) {
      case "overview":
        return <OverviewPage />;
      case "infrastructure":
        return <InfrastructurePage />;
      case "cicd":
        return <CicdPage />;
      case "kubernetes":
        return <KubernetesPage />;
      case "monitoring":
        return <MonitoringPage />;
      case "incidents":
        return <IncidentsPage />;
      case "healing":
        return <HealingEnginePage />;
      case "topology":
        return <TopologyPage />;
      case "audit":
        return <AuditLogsPage />;
      case "copilot":
        return <AICopilotPage />;
      case "settings":
        return <SettingsPage />;
      default:
        return <OverviewPage />;
    }
  };

  return (
    <div style={{ fontFamily: FONT_SANS, background: C.bg, height: "100vh", width: "100%", display: "flex", overflow: "hidden" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: ${C.border}; border-radius: 8px; }
        ::-webkit-scrollbar-thumb:hover { background: ${C.surface3}; }
        button { font-family: inherit; cursor: pointer; }
        input:focus { outline: none; }
        .topology-line {
          background: repeating-linear-gradient(to bottom, ${C.accent} 0 4px, transparent 4px 8px);
          animation: flow 0.6s linear infinite;
        }
        @keyframes flow { from { background-position: 0 0; } to { background-position: 0 16px; } }
        @media (prefers-reduced-motion: reduce) {
          * { animation-duration: 0.001ms !important; }
        }
      `}</style>
      <Sidebar active={page} onNavigate={setPage} collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        <TopBar pageTitle={PAGE_TITLES[page]} />
        <div style={{ flex: 1, overflowY: "auto" }}>
          {renderPage()}
        </div>
      </div>
    </div>
  );
}
