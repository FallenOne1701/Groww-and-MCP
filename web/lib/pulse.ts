import { cache } from "react";
import { W37_FIXTURE } from "./fixture";
import type { PulsePayload } from "./types";

const DEFAULT_HEALTH =
  "https://mcp-server-1-production.up.railway.app/health";

function publicDocUrl(): string | null {
  return process.env.NEXT_PUBLIC_PULSE_DOC_URL?.trim() || null;
}

async function mcpHealth(): Promise<boolean> {
  const url = process.env.NEXT_PUBLIC_MCP_HEALTH_URL?.trim() || DEFAULT_HEALTH;
  try {
    const response = await fetch(url, {
      cache: "no-store",
      signal: AbortSignal.timeout(4000),
    });
    if (!response.ok) return false;
    const body = (await response.json()) as { ok?: boolean; status?: string };
    if (typeof body.ok === "boolean") return body.ok;
    return body.status === "ok" || response.ok;
  } catch {
    return false;
  }
}

function applyPublicOverrides(payload: PulsePayload, mcpOk: boolean): PulsePayload {
  const docUrl = publicDocUrl() ?? payload.delivery.doc_url;
  return {
    ...payload,
    delivery: {
      ...payload.delivery,
      doc_url: docUrl,
      sent_id: null,
    },
    mcp: { ok: mcpOk, label: "mcp-server-1 · Railway" },
  };
}

export const getPulse = cache(async function getPulse(
  insufficient = false,
): Promise<PulsePayload> {
  const mcpOk = await mcpHealth();
  const apiUrl = process.env.PULSE_API_URL?.trim();

  if (apiUrl) {
    try {
      const headers: HeadersInit = {};
      const secret = process.env.PULSE_API_SECRET?.trim();
      if (secret) headers.Authorization = `Bearer ${secret}`;
      const response = await fetch(`${apiUrl.replace(/\/$/, "")}/api/pulse`, {
        headers,
        cache: "no-store",
        signal: AbortSignal.timeout(8000),
      });
      if (response.ok) {
        const remote = (await response.json()) as PulsePayload;
        return applyPublicOverrides(remote, mcpOk);
      }
    } catch {
      // Fall back to the committed W37 fixture.
    }
  }

  const fixture = structuredClone(W37_FIXTURE);
  if (insufficient) {
    fixture.insufficient_signal = true;
    fixture.validation_ok = false;
    fixture.gates.ok = false;
    fixture.delivery.delivery_skipped = true;
    fixture.delivery.doc_url = null;
    fixture.delivery.draft_id = null;
  }
  return applyPublicOverrides(fixture, mcpOk);
});

export async function checkMcpHealth(): Promise<{
  ok: boolean;
  label: string;
  url: string;
}> {
  const url = process.env.NEXT_PUBLIC_MCP_HEALTH_URL?.trim() || DEFAULT_HEALTH;
  return {
    ok: await mcpHealth(),
    label: "mcp-server-1 · Railway",
    url,
  };
}
