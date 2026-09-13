import { NextResponse } from "next/server";

export async function POST() {
  const apiUrl = process.env.PULSE_API_URL?.trim();
  if (!apiUrl) {
    return NextResponse.json(
      {
        accepted: false,
        message:
          "Run is handled by the Monday 08:00 IST scheduler — not this Vercel app.",
      },
      { status: 202 },
    );
  }

  const headers: HeadersInit = { "Content-Type": "application/json" };
  const secret = process.env.PULSE_API_SECRET?.trim();
  if (secret) headers.Authorization = `Bearer ${secret}`;

  const response = await fetch(`${apiUrl.replace(/\/$/, "")}/api/run`, {
    method: "POST",
    headers,
    signal: AbortSignal.timeout(8000),
  });

  const body = await response.json().catch(() => ({ accepted: true }));
  return NextResponse.json(body, { status: response.status || 202 });
}
