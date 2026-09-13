import { NextRequest, NextResponse } from "next/server";
import { getPulse } from "@/lib/pulse";

export async function GET(request: NextRequest) {
  const insufficient =
    request.nextUrl.searchParams.get("signal") === "empty";
  const payload = await getPulse(insufficient);
  return NextResponse.json(payload);
}
