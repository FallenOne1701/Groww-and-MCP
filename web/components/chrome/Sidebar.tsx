import Link from "next/link";
import { Icon } from "./Icon";
import { NAV } from "./nav";

export function Sidebar({
  pathname,
  mcpOk,
  product,
}: {
  pathname: string;
  mcpOk: boolean;
  product: string;
}) {
  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 flex-col justify-between border-r border-white/5 bg-sidebar p-4 lg:flex">
      <div>
        <div className="flex items-center justify-between px-2 pb-4 pt-1">
          <div className="flex items-center gap-2">
            <span className="inline-block size-3.5 rounded bg-accent shadow-sm" />
            <span className="text-lg font-bold tracking-tight text-white">
              {product.toLowerCase()}
            </span>
          </div>
          <span className="rounded border border-white/10 px-1.5 py-0.5 text-[11px] font-semibold tracking-wide text-sidebar-muted">
            DT
          </span>
        </div>
        <p className="mb-6 px-2 text-[11px] font-semibold uppercase tracking-[0.04em] text-sidebar-muted">
          Weekly Review Pulse
        </p>
        <nav className="space-y-1">
          {NAV.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={
                  active
                    ? "flex items-center gap-3 rounded-r-lg border-l-2 border-accent bg-accent/10 py-2.5 pl-4 text-accent"
                    : "flex items-center gap-3 rounded-lg py-2.5 pl-4 text-sidebar-muted transition-colors hover:bg-white/5 hover:text-sidebar-text"
                }
              >
                <Icon name={item.icon} filled={active} className={active ? "text-accent" : ""} />
                <span className="text-xs font-medium">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
      <div className="space-y-2 border-t border-white/10 px-2 pt-4">
        <div className="flex items-center gap-2 text-[11px] font-semibold text-sidebar-muted">
          <Icon
            name="check"
            className={mcpOk ? "text-accent" : "text-danger"}
          />
          <span>{mcpOk ? "MCP healthy" : "MCP down"}</span>
        </div>
        <div className="flex items-center gap-2 text-[11px] font-semibold text-sidebar-muted">
          <Icon name="shield" className="text-sidebar-muted" />
          <span>Play Store only · no PII</span>
        </div>
      </div>
    </aside>
  );
}
