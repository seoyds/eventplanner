"use client";

import { useState, useRef, useEffect, useMemo } from "react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface AgentStatuses {
  [key: string]: string;
}

export default function CopilotApp() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [agentStatuses, setAgentStatuses] = useState<AgentStatuses>({});
  const threadId = useMemo(() => crypto.randomUUID(), []);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || isStreaming) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: input.trim(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsStreaming(true);
    setAgentStatuses({});

    const assistantId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      { id: assistantId, role: "assistant", content: "" },
    ]);

    const fetchController = new AbortController();
    const fetchTimeout = setTimeout(() => fetchController.abort(), 10 * 60 * 1000); // 10 min

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
            if (
              event.type === "TEXT_MESSAGE_CONTENT" &&
              event.messageId === assistantId.toString()
            ) {
              // Skip — messageId won't match since server generates its own
            }
            if (event.type === "TEXT_MESSAGE_CONTENT") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: m.content + event.delta }
                    : m
                )
              );
            }
            if (event.type === "STATE_SNAPSHOT" && event.snapshot?.agent_statuses) {
              setAgentStatuses((prev) => ({
                ...prev,
                ...event.snapshot.agent_statuses,
              }));
            }
          } catch {
            // skip non-JSON lines
          }
        }
      }
    } catch (err) {
      // Append error to existing content (don't replace partial results)
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
    <div className="flex h-screen bg-white">
      {/* Chat Panel */}
      <div className="flex-1 flex flex-col">
        <div className="border-b px-6 py-4">
          <h1 className="text-xl font-semibold">Event Orchestrator</h1>
          <p className="text-sm text-gray-500">
            Describe your event — 10 specialist agents will plan it!
          </p>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-2 ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-900"
                }`}
              >
                <pre className="whitespace-pre-wrap font-sans text-sm">
                  {msg.content || (isStreaming ? "Thinking..." : "")}
                </pre>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div className="border-t px-6 py-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              placeholder="Describe your event..."
              className="flex-1 rounded-lg border px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isStreaming}
            />
            <button
              onClick={sendMessage}
              disabled={isStreaming || !input.trim()}
              className="rounded-lg bg-blue-600 px-6 py-2 text-white font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isStreaming ? "Planning..." : "Send"}
            </button>
          </div>
        </div>
      </div>

      {/* Agent Status Panel */}
      <div className="w-80 border-l bg-gray-50 p-4 space-y-3 overflow-y-auto">
        <h2 className="font-bold text-lg">Agent Status</h2>
        {Object.keys(agentStatuses).length === 0 ? (
          <p className="text-sm text-gray-400">
            Agents will appear here when active...
          </p>
        ) : (
          Object.entries(agentStatuses).map(([id, status]) => (
            <div key={id} className="flex items-center gap-2 text-sm">
              <span
                className={`w-2 h-2 rounded-full ${
                  status === "completed"
                    ? "bg-green-500"
                    : status === "running"
                    ? "bg-yellow-500 animate-pulse"
                    : status === "failed"
                    ? "bg-red-500"
                    : "bg-gray-300"
                }`}
              />
              <span className="capitalize">{id.replace(/_/g, " ")}</span>
              <span className="text-gray-400 text-xs">{status}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
