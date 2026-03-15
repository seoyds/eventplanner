import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const CONDUCTOR_URL =
  process.env.CONDUCTOR_INTERNAL_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  const body = await req.text();

  const resp = await fetch(`${CONDUCTOR_URL}/ag-ui`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: req.headers.get("accept") || "text/event-stream",
    },
    body,
  });

  return new Response(resp.body, {
    status: resp.status,
    headers: {
      "Content-Type": resp.headers.get("content-type") || "text/event-stream",
    },
  });
}

export async function GET() {
  const resp = await fetch(`${CONDUCTOR_URL}/ag-ui/info`);
  const data = await resp.json();
  return Response.json(data);
}
