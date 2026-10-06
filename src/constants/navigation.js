import {
  Gauge,
  ServerCog,
  GitBranch,
  Box,
  Activity,
  AlertTriangle,
  HeartPulse,
  Network,
  ScrollText,
  Sparkles,
  Settings as SettingsIcon,
} from "lucide-react";

export const NAV_GROUPS = [
  {
    label: "Observe",
    items: [
      { id: "overview", label: "Overview", icon: Gauge },
      { id: "infrastructure", label: "Infrastructure", icon: ServerCog },
      { id: "kubernetes", label: "Kubernetes", icon: Box },
      { id: "monitoring", label: "Monitoring", icon: Activity },
      { id: "topology", label: "Topology", icon: Network },
    ],
  },
  {
    label: "Automate",
    items: [
      { id: "cicd", label: "CI/CD Pipelines", icon: GitBranch },
      { id: "healing", label: "Healing Engine", icon: HeartPulse },
    ],
  },
  {
    label: "Respond",
    items: [
      { id: "incidents", label: "Incidents", icon: AlertTriangle },
      { id: "audit", label: "Audit Logs", icon: ScrollText },
    ],
  },
  {
    label: "Platform",
    items: [
      { id: "copilot", label: "AI Copilot", icon: Sparkles },
      { id: "settings", label: "Settings", icon: SettingsIcon },
    ],
  },
];

export const PAGE_TITLES = {
  overview: "Overview",
  infrastructure: "Infrastructure",
  cicd: "CI/CD Pipelines",
  kubernetes: "Kubernetes",
  monitoring: "Monitoring",
  incidents: "Incidents",
  healing: "Healing Engine",
  topology: "Topology",
  audit: "Audit Logs",
  copilot: "AI Copilot",
  settings: "Settings",
};
