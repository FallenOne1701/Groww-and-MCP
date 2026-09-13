import { productName } from "@/lib/format";
import { sitePassword } from "@/lib/auth";
import { redirect } from "next/navigation";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  if (!sitePassword()) redirect("/");
  const { error } = await searchParams;
  const product = productName();

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4">
      <div className="w-full max-w-md rounded-xl border border-hairline bg-surface p-8 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
        <div className="flex items-center gap-2">
          <span className="inline-block size-3.5 rounded bg-accent" />
          <span className="text-lg font-bold tracking-tight text-ink">
            {product.toLowerCase()}
          </span>
        </div>
        <p className="mt-1 text-[11px] font-semibold uppercase tracking-[0.04em] text-muted">
          Weekly Review Pulse
        </p>
        <p className="mt-5 text-[15px] leading-6 text-body">
          Internal briefing for Product, Support, and Leadership. Not the consumer
          Groww app.
        </p>
        <form action="/api/login" method="post" className="mt-6 space-y-4">
          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-[0.04em] text-muted">
              Shared password
            </span>
            <input
              name="password"
              type="password"
              required
              autoComplete="current-password"
              className="mt-2 h-9 w-full rounded-lg border border-hairline bg-surface px-3 text-[13px] text-ink placeholder:text-muted"
            />
          </label>
          {error ? (
            <p className="text-[13px] text-danger">That password did not match.</p>
          ) : null}
          <button
            type="submit"
            className="h-10 w-full rounded-lg bg-accent text-sm font-semibold text-white hover:bg-accent-hover"
          >
            Continue
          </button>
        </form>
        <p className="mt-6 text-[12px] text-muted">
          No Google login on this surface. Docs and Gmail stay on MCP.
        </p>
      </div>
    </div>
  );
}
