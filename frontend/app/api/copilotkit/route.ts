import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const maxDuration = 300; // 5 minutes max for agent orchestration

const CONDUCTOR_URL =
  process.env.CONDUCTOR_INTERNAL_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  const body = await req.text();

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10 * 60 * 1000); // 10 min

  try {
    const resp = await fetch(`${CONDUCTOR_URL}/ag-ui`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: req.headers.get("accept") || "text/event-stream",
      },
      body,
      signal: controller.signal,
    });

    return new Response(resp.body, {
      status: resp.status,
      headers: {
        "Content-Type": resp.headers.get("content-type") || "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  } finally {
    clearTimeout(timeout);
  }
}

export async function GET() {
  const resp = await fetch(`${CONDUCTOR_URL}/ag-ui/info`);
  const data = await resp.json();
  return Response.json(data);
}
