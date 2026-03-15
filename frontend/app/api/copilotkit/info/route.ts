export const dynamic = "force-dynamic";

const CONDUCTOR_URL =
  process.env.CONDUCTOR_INTERNAL_URL || "http://localhost:8000";

export async function GET() {
  const resp = await fetch(`${CONDUCTOR_URL}/ag-ui/info`);
  const data = await resp.json();
  return Response.json(data);
}
