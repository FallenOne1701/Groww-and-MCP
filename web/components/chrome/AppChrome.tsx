"use client";

import type { PulsePayload } from "@/lib/types";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { MobileTabBar } from "./MobileTabBar";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

export function AppChrome({
  pulse,
  product,
  children,
}: {
  pulse: PulsePayload;
  product: string;
  children: ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-canvas">
      <Sidebar pathname={pathname} mcpOk={pulse.mcp.ok} product={product} />
      <div className="flex min-h-screen flex-col lg:pl-60">
        <TopBar pathname={pathname} pulse={pulse} />
        <main className="flex-1 px-4 pb-36 pt-6 lg:px-8 lg:pb-10">{children}</main>
      </div>
      <MobileTabBar
        pathname={pathname}
        docUrl={pulse.delivery.doc_url}
        hideDoc={pulse.insufficient_signal || !pulse.validation_ok}
      />
    </div>
  );
}
