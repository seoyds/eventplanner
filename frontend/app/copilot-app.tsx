"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { useCoAgentStateRender } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";

function AgentMonitor() {
  useCoAgentStateRender({
    name: "conductor",
    render: ({ state }) => (
      <div className="p-4 space-y-3">
        <h2 className="font-bold text-lg">Agent Status</h2>
        {Object.entries((state?.agent_statuses as Record<string, string>) || {}).map(
          ([id, status]) => (
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
          )
        )}
      </div>
    ),
  });
  return null;
}

export default function CopilotApp() {
  const runtimeUrl =
    process.env.NEXT_PUBLIC_CONDUCTOR_URL || "http://localhost:8000/ag-ui";

  return (
    <CopilotKit runtimeUrl={runtimeUrl}>
      <div className="flex h-screen">
        <div className="flex-1">
          <CopilotChat
            labels={{
              title: "Event Orchestrator",
              initial:
                "Describe your event — I'll coordinate 10 specialist agents to plan it!",
            }}
          />
        </div>
        <div className="w-80 border-l bg-gray-50">
          <AgentMonitor />
        </div>
      </div>
    </CopilotKit>
  );
}
