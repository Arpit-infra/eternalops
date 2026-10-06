import {
  CheckCircle2,
  HeartPulse,
  BrainCircuit,
  AlertTriangle,
  ShieldAlert,
  CircleDot,
  Box,
  GitBranch,
  Activity,
  BarChart3,
  ShieldCheck,
  Mail,
  Database,
} from "lucide-react";
import { C } from "../constants/theme";
import { buildSeries } from "../utils/formatters";

export const cpuSeries = buildSeries(24, 38, 3, { spikeAt: 12, spikeMag: 55, recoverAt: 17, max: 100 });
export const memSeries = buildSeries(24, 45, 2, { spikeAt: 8, spikeMag: 48, recoverAt: 17, max: 100 });
export const latencySeries = buildSeries(24, 40, 4, { spikeAt: 12, spikeMag: 90, recoverAt: 16, max: 260 });
export const reqSeries = buildSeries(24, 2200, 150, { min: 1200, max: 3200 });
export const netSeries = buildSeries(24, 320, 30, { min: 100, max: 700 });
export const diskSeries = buildSeries(24, 61, 1.2, { min: 50, max: 80 });
export const errSeries = buildSeries(24, 0.3, 0.15, { spikeAt: 12, spikeMag: 4.2, recoverAt: 16, min: 0, max: 6 });

export const activityFeed = [
  { t: "14:38:02", type: "success", text: "Pipeline eternal-api#4471 succeeded", meta: "main · 2m 14s" },
  { t: "14:36:41", type: "success", text: "Cluster stabilized", meta: "prod-use1 · all nodes green" },
  { t: "14:35:58", type: "heal", text: "Rollback completed", meta: "checkout-svc → v2.8.1" },
  { t: "14:34:12", type: "ai", text: "AI recommended rollback", meta: "confidence 94%" },
  { t: "14:33:47", type: "warning", text: "Prometheus fired alert HighMemUsage", meta: "checkout-svc" },
  { t: "14:32:10", type: "critical", text: "Backend pod restarted x3", meta: "checkout-svc-7f9c" },
  { t: "14:29:03", type: "info", text: "Deployment checkout-svc v2.9.0 shipped", meta: "by nadia.k" },
  { t: "14:11:55", type: "success", text: "Trivy scan completed — 0 critical CVEs", meta: "auth-svc:1.4.2" },
  { t: "13:58:20", type: "info", text: "SonarQube quality gate passed", meta: "billing-svc" },
  { t: "13:40:07", type: "success", text: "Healed: node cordon cleared", meta: "node-gke-3" },
];

export const feedIcon = {
  success: { icon: CheckCircle2, color: C.success },
  heal: { icon: HeartPulse, color: C.accent },
  ai: { icon: BrainCircuit, color: C.violet },
  warning: { icon: AlertTriangle, color: C.warning },
  critical: { icon: ShieldAlert, color: C.critical },
  info: { icon: CircleDot, color: C.info },
};

export const infraServices = [
  { name: "Kubernetes", icon: Box, status: "Operational", version: "v1.29.4", health: 99, lastSync: "12s ago" },
  { name: "Jenkins", icon: GitBranch, status: "Operational", version: "2.462.1", health: 100, lastSync: "34s ago" },
  { name: "Prometheus", icon: Activity, status: "Operational", version: "v2.53.0", health: 98, lastSync: "8s ago" },
  { name: "Grafana", icon: BarChart3, status: "Operational", version: "11.1.0", health: 100, lastSync: "20s ago" },
  { name: "SonarQube", icon: ShieldCheck, status: "Degraded", version: "10.5.1", health: 82, lastSync: "3m ago" },
  { name: "Trivy", icon: ShieldAlert, status: "Operational", version: "0.52.2", health: 100, lastSync: "1m ago" },
  { name: "SMTP Relay", icon: Mail, status: "Operational", version: "postfix 3.8", health: 100, lastSync: "45s ago" },
  { name: "PostgreSQL", icon: Database, status: "Operational", version: "16.3", health: 97, lastSync: "6s ago" },
];

export const pipelines = [
  { name: "eternal-api", branch: "main", commit: "a4f91c2", author: "nadia.k", status: "Success", duration: "2m 14s" },
  { name: "checkout-svc", branch: "release/2.9", commit: "9c2e0aa", author: "raj.p", status: "Running", duration: "1m 02s" },
  { name: "auth-svc", branch: "main", commit: "0f7b3d1", author: "elin.w", status: "Success", duration: "3m 41s" },
  { name: "billing-svc", branch: "feature/invoices", commit: "5b8a19e", author: "tomás.f", status: "Failed", duration: "0m 58s" },
  { name: "web-frontend", branch: "main", commit: "e12ac70", author: "nadia.k", status: "Success", duration: "4m 05s" },
  { name: "notification-svc", branch: "main", commit: "77dfe4c", author: "kai.s", status: "Queued", duration: "—" },
  { name: "inventory-svc", branch: "hotfix/stock-sync", commit: "b90c2f1", author: "raj.p", status: "Success", duration: "1m 47s" },
  { name: "search-svc", branch: "main", commit: "31aa8d0", author: "elin.w", status: "Running", duration: "0m 39s" },
];

export const namespaces = ["production", "staging", "monitoring", "ingress", "data", "healing-system"];

export const deployments = [
  { name: "checkout-svc", ns: "production", replicas: "3/3", restarts: 2, cpu: 64, mem: 71 },
  { name: "auth-svc", ns: "production", replicas: "4/4", restarts: 0, cpu: 28, mem: 34 },
  { name: "billing-svc", ns: "production", replicas: "2/2", restarts: 1, cpu: 41, mem: 52 },
  { name: "web-frontend", ns: "production", replicas: "6/6", restarts: 0, cpu: 19, mem: 22 },
  { name: "prometheus", ns: "monitoring", replicas: "1/1", restarts: 0, cpu: 33, mem: 58 },
  { name: "grafana", ns: "monitoring", replicas: "1/1", restarts: 0, cpu: 12, mem: 26 },
  { name: "healing-controller", ns: "healing-system", replicas: "2/2", restarts: 0, cpu: 8, mem: 15 },
  { name: "ingress-nginx", ns: "ingress", replicas: "3/3", restarts: 0, cpu: 22, mem: 19 },
];

// Deterministic static status distribution for UI preview
export const podHealth = [
  "healthy", "healthy", "healthy", "healthy", "warning", "healthy", "healthy", "healthy",
  "healthy", "healthy", "critical", "healthy", "healthy", "healthy", "healthy", "healthy",
  "healthy", "warning", "healthy", "healthy", "healthy", "healthy", "healthy", "healthy",
  "healthy", "healthy", "healthy", "healthy", "healthy", "warning", "healthy", "healthy",
  "healthy", "healthy", "healthy", "critical", "healthy", "healthy", "healthy", "healthy",
  "healthy", "healthy", "healthy", "warning", "healthy", "healthy", "healthy", "healthy",
];

export const incidentsData = [
  {
    id: "INC-2291",
    title: "Memory leak in checkout-svc causing pod restarts",
    severity: "critical",
    service: "checkout-svc",
    opened: "14:32:04",
    recovery: "3m 42s",
    status: "Resolved",
    rootCause: "Deployment v2.9.0 introduced an unbounded in-memory cache for session tokens, exhausting heap and triggering OOM kills under peak load.",
    confidence: 94,
    action: "Automatic rollback to v2.8.1 + pod eviction & reschedule",
    logs: "OOMKilled: container checkout-svc exceeded memory limit 512Mi\nWARN  heap usage 96% — GC pressure critical\nINFO  rollback initiated by healing-controller",
    metrics: "Memory 45% → 93% over 8m · CPU 38% → 91% · Error rate 0.3% → 4.4%",
  },
  {
    id: "INC-2288",
    title: "Elevated latency on payment gateway",
    severity: "warning",
    service: "billing-svc",
    opened: "11:04:12",
    recovery: "6m 10s",
    status: "Resolved",
    rootCause: "Upstream PSP experienced regional slowdown, increasing p95 latency for payment authorization calls.",
    confidence: 87,
    action: "Traffic shifted to secondary PSP endpoint",
    logs: "WARN  p95 latency 1240ms exceeds SLO 400ms\nINFO  circuit breaker opened for psp-primary\nINFO  traffic rerouted to psp-secondary",
    metrics: "Latency 90ms → 1240ms · Requests/sec stable at 2.1k",
  },
  {
    id: "INC-2277",
    title: "Node disk pressure on gke-node-3",
    severity: "warning",
    service: "kubernetes",
    opened: "09:47:33",
    recovery: "2m 58s",
    status: "Resolved",
    rootCause: "Orphaned container images accumulated disk usage past the eviction threshold.",
    confidence: 91,
    action: "Automated image garbage collection + node cordon/uncordon",
    logs: "WARN  DiskPressure condition on node gke-node-3\nINFO  garbage collection freed 8.2Gi\nINFO  node uncordoned, scheduling resumed",
    metrics: "Disk usage 92% → 61% · Node ready in 2m 58s",
  },
  {
    id: "INC-2301",
    title: "SonarQube quality gate degraded on billing-svc",
    severity: "info",
    service: "sonarqube",
    opened: "13:58:20",
    recovery: "—",
    status: "Investigating",
    rootCause: "Pending analysis — new test coverage regression detected on feature branch.",
    confidence: 62,
    action: "Awaiting engineer review",
    logs: "INFO  quality gate: coverage 78% (threshold 80%)\nWARN  2 new code smells introduced",
    metrics: "Coverage 84% → 78% · Duplication 3.1% → 3.4%",
  },
];

export const auditLogs = [
  { ts: "14:38:02", action: "Pipeline deployment", by: "CI/CD Bot", target: "eternal-api", cluster: "prod-use1", duration: "2m 14s", status: "Success" },
  { ts: "14:35:58", action: "Automated rollback", by: "Healing Engine", target: "checkout-svc", cluster: "prod-use1", duration: "41s", status: "Success" },
  { ts: "14:34:12", action: "AI recommendation issued", by: "AI Copilot", target: "checkout-svc", cluster: "prod-use1", duration: "3s", status: "Success" },
  { ts: "14:29:03", action: "Manual deployment", by: "nadia.k", target: "checkout-svc", cluster: "prod-use1", duration: "1m 58s", status: "Success" },
  { ts: "13:40:07", action: "Node uncordon", by: "Healing Engine", target: "gke-node-3", cluster: "prod-use1", duration: "6s", status: "Success" },
  { ts: "13:12:45", action: "API key rotated", by: "elin.w", target: "grafana-svc-key", cluster: "—", duration: "1s", status: "Success" },
  { ts: "12:58:31", action: "Pipeline deployment", by: "CI/CD Bot", target: "billing-svc", cluster: "prod-use1", duration: "0m 58s", status: "Failed" },
  { ts: "11:04:12", action: "Traffic failover", by: "Healing Engine", target: "billing-svc", cluster: "prod-use1", duration: "9s", status: "Success" },
  { ts: "09:47:33", action: "Image garbage collection", by: "Healing Engine", target: "gke-node-3", cluster: "prod-use1", duration: "22s", status: "Success" },
  { ts: "08:15:02", action: "SMTP config updated", by: "raj.p", target: "notification-svc", cluster: "—", duration: "1s", status: "Success" },
  { ts: "07:40:19", action: "Cluster scale-up", by: "System", target: "prod-use1", cluster: "prod-use1", duration: "2m 30s", status: "Success" },
  { ts: "06:02:55", action: "Trivy scan", by: "CI/CD Bot", target: "auth-svc:1.4.2", cluster: "—", duration: "38s", status: "Success" },
];

export const suggestedPrompts = [
  "Why did backend restart?",
  "Generate incident summary.",
  "Suggest recovery.",
  "Explain this deployment.",
  "Generate postmortem.",
];

export const cannedResponses = {
  "Why did backend restart?": "checkout-svc restarted 3 times between 14:32 and 14:35. Root cause: deployment v2.9.0 introduced an unbounded in-memory session cache, exhausting the 512Mi heap limit and triggering OOMKilled events. The healing controller detected the pattern via Prometheus's HighMemUsage alert and rolled back to v2.8.1 automatically. No customer-facing errors were recorded after 14:36.",
  "Generate incident summary.": "INC-2291 — Memory leak in checkout-svc. Detected 14:32:04, resolved 14:35:46 (3m 42s). Severity: Critical. Root cause: unbounded session cache from v2.9.0. Action: automatic rollback + pod eviction. Verification: memory usage returned to 45% baseline, error rate dropped from 4.4% to 0.3%. No manual intervention required.",
  "Suggest recovery.": "Recommend: 1) Roll back checkout-svc to v2.8.1 (already applied). 2) Add a bounded LRU eviction policy to the session cache before re-attempting v2.9.0. 3) Add a memory-based HPA trigger at 70% to scale horizontally before OOM thresholds are hit. 4) Add a canary stage to the pipeline gating on memory growth over 15 minutes.",
  "Explain this deployment.": "checkout-svc v2.9.0 shipped at 14:29 by nadia.k via the eternal-api pipeline. It introduced a new session caching layer intended to reduce database reads by 30%. The change was not bounded by a max-entry limit, which is the underlying cause of the incident detected 3 minutes after rollout.",
  "Generate postmortem.": "Postmortem draft — INC-2291\n\nImpact: Elevated latency and 3 pod restarts on checkout-svc for 3m 42s. No data loss. Estimated 0.02% of checkout sessions affected.\n\nTimeline: 14:29 deploy · 14:32 memory alert fired · 14:33 pods began OOM-killing · 14:34 AI Copilot recommended rollback (94% confidence) · 14:35 rollback completed · 14:36 cluster stabilized.\n\nAction items: bound the session cache, add memory-based canary gating, expand HPA thresholds.",
};
