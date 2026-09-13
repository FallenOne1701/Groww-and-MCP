"use client";

import Link from "next/link";
import { useState } from "react";
import { Icon } from "./Icon";
import { MOBILE_TABS, NAV } from "./nav";

export function MobileTabBar({
  pathname,
  docUrl,
  hideDoc,
}: {
  pathname: string;
  docUrl: string | null;
  hideDoc: boolean;
}) {
  const [moreOpen, setMoreOpen] = useState(false);
  const overflow = NAV.filter(
    (item) => !MOBILE_TABS.some((tab) => tab.href === item.href),
  );

  return (
    <>
      {!hideDoc && docUrl ? (
        <div className="fixed inset-x-0 bottom-16 z-40 border-t border-hairline bg-surface px-4 py-2 lg:hidden">
          <a
            href={docUrl}
            target="_blank"
            rel="noreferrer"
            className="flex h-10 items-center justify-center rounded-lg bg-accent text-sm font-semibold text-white hover:bg-accent-hover"
          >
            Open Doc
          </a>
        </div>
      ) : null}

      {moreOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-ink/40"
            aria-label="Close more"
            onClick={() => setMoreOpen(false)}
          />
          <div className="absolute inset-x-0 bottom-0 rounded-t-2xl bg-surface p-4 pb-8 shadow-[0_4px_12px_rgba(11,13,18,0.08)]">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-muted">
                More
              </p>
              <button
                type="button"
                onClick={() => setMoreOpen(false)}
                className="rounded-lg p-1 text-body hover:bg-accent-soft hover:text-accent"
                aria-label="Close"
              >
                <Icon name="close" />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {overflow.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMoreOpen(false)}
                  className="flex items-center gap-2 rounded-xl border border-hairline px-3 py-3 text-sm font-medium text-ink hover:bg-canvas"
                >
                  <Icon name={item.icon} />
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
        </div>
      ) : null}

      <nav className="fixed inset-x-0 bottom-0 z-40 flex h-16 items-center justify-around border-t border-hairline bg-surface lg:hidden">
        {MOBILE_TABS.map((tab) => {
          const active = pathname === tab.href;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`flex flex-col items-center gap-1 text-[11px] font-semibold ${
                active ? "text-accent" : "text-muted"
              }`}
            >
              <Icon name={tab.icon} filled={active} />
              {tab.label}
            </Link>
          );
        })}
        <button
          type="button"
          onClick={() => setMoreOpen(true)}
          className={`flex flex-col items-center gap-1 text-[11px] font-semibold ${
            overflow.some((item) => item.href === pathname)
              ? "text-accent"
              : "text-muted"
          }`}
        >
          <Icon name="more" />
          More
        </button>
      </nav>
    </>
  );
}
