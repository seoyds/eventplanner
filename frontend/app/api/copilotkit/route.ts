import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const maxDuration = 600; // 10 minutes max for agent orchestration

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
      keepalive: true,
    });

    // Actively read and forward chunks with proxy-level keepalives
    // to prevent Cloudflare/browser from dropping idle SSE connections
    const upstream = resp.body;
    if (!upstream) {
      return new Response("No upstream body", { status: 502 });
    }

    const encoder = new TextEncoder();
    const KEEPALIVE = encoder.encode(": keepalive\n\n");
    const KEEPALIVE_INTERVAL = 5000; // 5 seconds

    const stream = new ReadableStream({
      async start(ctrl) {
        const reader = upstream.getReader();
        let keepaliveTimer: ReturnType<typeof setInterval> | null = null;

        // Send keepalives while waiting for upstream data
        keepaliveTimer = setInterval(() => {
          try {
            ctrl.enqueue(KEEPALIVE);
          } catch {
            // stream already closed
            if (keepaliveTimer) clearInterval(keepaliveTimer);
          }
        }, KEEPALIVE_INTERVAL);

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            ctrl.enqueue(value);
          }
        } catch {
          // upstream closed or errored — close gracefully
        } finally {
          if (keepaliveTimer) clearInterval(keepaliveTimer);
          ctrl.close();
        }
      },
    });

    return new Response(stream, {
      status: resp.status,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
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
