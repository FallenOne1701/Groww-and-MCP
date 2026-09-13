const COOKIE = "pulse_access";

export function accessCookieName(): string {
  return COOKIE;
}

export function sitePassword(): string | undefined {
  const value = process.env.PULSE_SITE_PASSWORD?.trim();
  return value ? value : undefined;
}

export async function accessToken(secret: string): Promise<string> {
  const data = new TextEncoder().encode(`groww-pulse:${secret}`);
  const hash = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(hash), (b) =>
    b.toString(16).padStart(2, "0"),
  ).join("");
}
