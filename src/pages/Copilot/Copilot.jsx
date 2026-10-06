import { useState, useEffect, useRef } from "react";
import { Sparkles, User, Send, Zap } from "lucide-react";
import { C } from "../../constants/theme";
import { suggestedPrompts } from "../../data/dashboardData";
import { aiService } from "../../services/aiService";

export function AICopilotPage() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Hi, I'm the EternalOps Copilot. I analyze live Kubernetes cluster telemetry, Prometheus anomaly alerts, active self-healing pipelines, and audit logs. How can I assist you?",
      suggested_actions: [],
    },
  ]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, thinking]);

  async function send(text) {
    const q = text ?? input;
    if (!q || !q.trim()) return;

    setMessages((m) => [...m, { role: "user", text: q }]);
    setInput("");
    setThinking(true);

    try {
      const res = await aiService.chat(q);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: res.response,
          suggested_actions: res.suggested_actions || [],
        },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: "Error communicating with AI Copilot backend. Please ensure the backend server is reachable.",
          suggested_actions: [],
        },
      ]);
    } finally {
      setThinking(false);
    }
  }

  return (
    <div className="p-6 h-full flex flex-col gap-4" style={{ maxWidth: 860, margin: "0 auto", width: "100%" }}>
      <div>
        <h2 className="text-lg font-semibold flex items-center gap-2" style={{ color: C.textPrimary }}>
          <Sparkles size={18} style={{ color: C.violet }} /> AI Copilot
        </h2>
        <p className="text-sm mt-0.5" style={{ color: C.textTertiary }}>
          Context-aware assistant querying live Kubernetes, Prometheus, and Self-Healing telemetry
        </p>
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto rounded-2xl p-6 flex flex-col gap-4"
        style={{ background: C.surface, border: `1px solid ${C.border}`, minHeight: 380, maxHeight: 480 }}
      >
        {messages.map((m, i) => (
          <div key={i} className={`flex flex-col gap-2 ${m.role === "user" ? "items-end" : "items-start"}`}>
            <div className={`flex gap-3 ${m.role === "user" ? "flex-row-reverse" : ""}`}>
              <div
                className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
                style={{ background: m.role === "user" ? C.surface3 : C.violetSoft }}
              >
                {m.role === "user" ? (
                  <User size={13} style={{ color: C.textSecondary }} />
                ) : (
                  <Sparkles size={13} style={{ color: C.violet }} />
                )}
              </div>
              <div
                className="rounded-2xl px-4 py-3 text-[13px] leading-relaxed whitespace-pre-line"
                style={{
                  background: m.role === "user" ? C.surface2 : C.surface3,
                  color: C.textPrimary,
                  maxWidth: "85%",
                }}
              >
                {m.text}
              </div>
            </div>

            {/* Suggested Follow-up Actions if any */}
            {m.suggested_actions && m.suggested_actions.length > 0 && (
              <div className="flex gap-1.5 flex-wrap ml-10">
                {m.suggested_actions.map((act) => (
                  <button
                    key={act}
                    onClick={() => send(act)}
                    className="flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium cursor-pointer transition-colors"
                    style={{ background: C.surface2, border: `1px solid ${C.border}`, color: C.textSecondary }}
                  >
                    <Zap size={10} style={{ color: C.accent }} /> {act}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}

        {thinking && (
          <div className="flex gap-3">
            <div
              className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
              style={{ background: C.violetSoft }}
            >
              <Sparkles size={13} style={{ color: C.violet }} />
            </div>
            <div className="rounded-2xl px-4 py-3 flex items-center gap-1" style={{ background: C.surface3 }}>
              {[0, 1, 2].map((d) => (
                <span
                  key={d}
                  className="w-1.5 h-1.5 rounded-full animate-bounce"
                  style={{ background: C.textTertiary, animationDelay: `${d * 120}ms` }}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="flex gap-2 flex-wrap">
        {suggestedPrompts.map((p) => (
          <button
            key={p}
            onClick={() => send(p)}
            className="px-3 py-1.5 rounded-full text-xs font-medium cursor-pointer transition-colors"
            style={{ background: C.surface2, border: `1px solid ${C.border}`, color: C.textSecondary }}
          >
            {p}
          </button>
        ))}
      </div>

      <div
        className="flex items-center gap-2 rounded-xl px-3 py-2"
        style={{ background: C.surface2, border: `1px solid ${C.border}` }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask about an incident, pod restart, deployment status, or recovery strategy…"
          className="flex-1 bg-transparent outline-none text-[13px]"
          style={{ color: C.textPrimary }}
        />
        <button
          onClick={() => send()}
          disabled={thinking || !input.trim()}
          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 cursor-pointer disabled:opacity-50"
          style={{ background: C.violetSoft }}
        >
          <Send size={14} style={{ color: C.violet }} />
        </button>
      </div>
    </div>
  );
}

export default AICopilotPage;
