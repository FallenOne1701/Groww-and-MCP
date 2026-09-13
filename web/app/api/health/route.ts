import { NextResponse } from "next/server";
import { checkMcpHealth } from "@/lib/pulse";

export async function GET() {
  const health = await checkMcpHealth();
  return NextResponse.json(health);
}
