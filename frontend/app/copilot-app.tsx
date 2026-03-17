"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  A2UISurfaceRenderer,
  parseA2UIMessages,
  type A2UISurface,
  type A2UIMessage,
} from "./components/a2ui-renderer";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  /** A2UI surfaces attached to this assistant message */
  surfaces: A2UISurface[];
}

interface AgentStatuses {
  [key: string]: string;
}

export default function CopilotApp() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [agentStatuses, setAgentStatuses] = useState<AgentStatuses>({});
  const [showAgentPanel, setShowAgentPanel] = useState(false);
  const threadId = useMemo(() => crypto.randomUUID(), []);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const activeAgentCount = Object.keys(agentStatuses).length;
  const runningCount = Object.values(agentStatuses).filter((s) => s === "running").length;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || isStreaming) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: input.trim(),
      surfaces: [],
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsStreaming(true);
    setAgentStatuses({});

    const assistantId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      { id: assistantId, role: "assistant", content: "", surfaces: [] },
    ]);

    const fetchController = new AbortController();
    const fetchTimeout = setTimeout(() => fetchController.abort(), 10 * 60 * 1000); // 10 min

    // Use Next.js proxy (same-origin, no CORS issues)
    try {
      const resp = await fetch("/api/copilotkit", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        signal: fetchController.signal,
        body: JSON.stringify({
          method: "agent/run",
          params: { agentId: "default" },
          body: {
            threadId: threadId,
            runId: crypto.randomUUID(),
            messages: [
              ...messages.map((m) => ({ id: m.id, role: m.role, content: m.content })),
              { id: userMsg.id, role: "user", content: userMsg.content },
            ],
            tools: [],
            context: [],
            forwardedProps: {},
            state: {},
          },
        }),
      });

      const reader = resp.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error("No response body");

      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(line.slice(6));

            // Text content streaming
            if (event.type === "TEXT_MESSAGE_CONTENT") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: m.content + event.delta }
                    : m
                )
              );
            }

            // State snapshots: agent statuses and A2UI surfaces
            if (event.type === "STATE_SNAPSHOT") {
              if (event.snapshot?.agent_statuses) {
                setAgentStatuses((prev) => ({
                  ...prev,
                  ...event.snapshot.agent_statuses,
                }));
              }

              // A2UI surface messages
              if (event.snapshot?.a2ui_messages) {
                const a2uiMsgs = event.snapshot.a2ui_messages as A2UIMessage[];
                setMessages((prev) =>
                  prev.map((m) => {
                    if (m.id !== assistantId) return m;
                    // Find or create the surface
                    const surfaceId = _extractSurfaceId(a2uiMsgs);
                    const existing = m.surfaces.find(
                      (s) => s.surfaceId === surfaceId
                    );
                    const updated = parseA2UIMessages(
                      a2uiMsgs,
                      existing || undefined
                    );
                    const newSurfaces = existing
                      ? m.surfaces.map((s) =>
                          s.surfaceId === surfaceId ? updated : s
                        )
                      : [...m.surfaces, updated];
                    return { ...m, surfaces: newSurfaces };
                  })
                );
              }
            }
          } catch {
            // skip non-JSON lines
          }
        }
      }
    } catch (err) {
      const errMsg = err instanceof Error && err.name === "AbortError"
        ? "\n\n[Timed out — partial results shown above]"
        : `\n\n[Error: ${err}]`;
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: m.content + errMsg }
            : m
        )
      );
    } finally {
      clearTimeout(fetchTimeout);
      setIsStreaming(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-50 relative">
      {/* Chat Panel */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="border-b bg-white px-4 sm:px-6 py-3 sm:py-4 shadow-sm flex items-center justify-between">
          <div>
            <h1 className="text-lg sm:text-xl font-semibold text-gray-900">Event Orchestrator</h1>
            <p className="text-xs sm:text-sm text-gray-500">
              Describe your event — 10 specialist agents will plan it!
            </p>
          </div>
          {/* Mobile agent panel toggle */}
          {activeAgentCount > 0 && (
            <button
              onClick={() => setShowAgentPanel(!showAgentPanel)}
              className="lg:hidden flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gray-100 text-sm font-medium text-gray-700 hover:bg-gray-200 transition-colors"
            >
              <span className={`w-2 h-2 rounded-full ${runningCount > 0 ? "bg-yellow-500 animate-pulse" : "bg-green-500"}`} />
              {runningCount > 0 ? `${runningCount} running` : `${activeAgentCount} done`}
            </button>
          )}
        </div>

        <div className="flex-1 overflow-y-auto px-3 sm:px-6 py-3 sm:py-4 space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[95%] sm:max-w-[85%] rounded-xl px-3 sm:px-4 py-2 sm:py-3 ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white shadow-sm"
                    : "bg-white text-gray-900 shadow-sm border border-gray-100"
                }`}
              >
                {msg.role === "user" ? (
                  <p className="text-sm">{msg.content}</p>
                ) : (
                  <AssistantMessageContent message={msg} isStreaming={isStreaming} />
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div className="border-t bg-white px-3 sm:px-6 py-3 sm:py-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              placeholder="Describe your event..."
              className="flex-1 rounded-xl border border-gray-300 px-3 sm:px-4 py-2 sm:py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isStreaming}
            />
            <button
              onClick={sendMessage}
              disabled={isStreaming || !input.trim()}
              className="rounded-xl bg-blue-600 px-4 sm:px-6 py-2 sm:py-2.5 text-sm text-white font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
            >
              {isStreaming ? "..." : "Send"}
            </button>
          </div>
        </div>
      </div>

      {/* Agent Status Panel — sidebar on desktop, slide-over on mobile */}
      {showAgentPanel && (
        <div
          className="fixed inset-0 bg-black/30 z-40 lg:hidden"
          onClick={() => setShowAgentPanel(false)}
        />
      )}
      <div
        className={`
          fixed right-0 top-0 h-full w-72 sm:w-80 bg-white shadow-xl z-50 transform transition-transform duration-300 ease-in-out
          lg:static lg:transform-none lg:shadow-none lg:border-l lg:z-auto
          ${showAgentPanel ? "translate-x-0" : "translate-x-full lg:translate-x-0"}
        `}
      >
        <div className="p-4 space-y-3 overflow-y-auto h-full">
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-lg text-gray-900">Agent Status</h2>
            <button
              onClick={() => setShowAgentPanel(false)}
              className="lg:hidden p-1 rounded-lg hover:bg-gray-100 text-gray-500"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          {activeAgentCount === 0 ? (
            <p className="text-sm text-gray-400">
              Agents will appear here when active...
            </p>
          ) : (
            Object.entries(agentStatuses).map(([id, status]) => (
              <div key={id} className="flex items-center gap-2.5 text-sm py-1">
                <span
                  className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
                    status === "completed"
                      ? "bg-green-500"
                      : status === "running"
                      ? "bg-yellow-500 animate-pulse"
                      : status === "failed"
                      ? "bg-red-500"
                      : "bg-gray-300"
                  }`}
                />
                <span className="capitalize font-medium text-gray-700">
                  {id.replace(/_/g, " ")}
                </span>
                <span className="text-gray-400 text-xs ml-auto">{status}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Assistant Message with A2UI + Markdown rendering ───────────────────────

function AssistantMessageContent({
  message,
  isStreaming,
}: {
  message: Message;
  isStreaming: boolean;
}) {
  const hasContent = message.content.trim().length > 0;
  const hasSurfaces = message.surfaces.length > 0;

  if (!hasContent && !hasSurfaces) {
    return (
      <p className="text-sm text-gray-400 animate-pulse">
        {isStreaming ? "Thinking..." : ""}
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {/* Rendered markdown text */}
      {hasContent && (
        <div className="prose prose-sm prose-gray max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        </div>
      )}

      {/* A2UI Surfaces */}
      {hasSurfaces && (
        <div className="space-y-4 mt-3">
          {message.surfaces.map((surface) => (
            <A2UISurfaceRenderer
              key={surface.surfaceId}
              surface={surface}
              onAction={(actionName, context) => {
                console.log("A2UI action:", actionName, context);
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function _extractSurfaceId(messages: A2UIMessage[]): string {
  for (const msg of messages) {
    if (msg.createSurface?.surfaceId) return msg.createSurface.surfaceId;
    if (msg.updateComponents?.surfaceId) return msg.updateComponents.surfaceId;
    if (msg.updateDataModel?.surfaceId) return msg.updateDataModel.surfaceId;
  }
  return "default";
}
