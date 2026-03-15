"use client";

import dynamic from "next/dynamic";

const CopilotApp = dynamic(() => import("./copilot-app"), { ssr: false });

export default function Home() {
  return <CopilotApp />;
}
