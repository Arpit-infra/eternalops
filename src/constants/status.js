import { C } from "../constants/theme";

export const statusMeta = {
  Success: { color: C.success, bg: C.successSoft },
  Operational: { color: C.success, bg: C.successSoft },
  Running: { color: C.info, bg: C.infoSoft },
  Failed: { color: C.critical, bg: C.criticalSoft },
  Degraded: { color: C.warning, bg: C.warningSoft },
  Queued: { color: C.textSecondary, bg: "rgba(154,156,166,0.12)" },
  Resolved: { color: C.success, bg: C.successSoft },
  Active: { color: C.critical, bg: C.criticalSoft },
  Investigating: { color: C.warning, bg: C.warningSoft },
};
