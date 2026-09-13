import { AppChrome } from "@/components/chrome/AppChrome";
import { productName } from "@/lib/format";
import { getPulse } from "@/lib/pulse";
import type { ReactNode } from "react";

export default async function AppLayout({
  children,
}: {
  children: ReactNode;
}) {
  const pulse = await getPulse();

  return (
    <AppChrome pulse={pulse} product={productName()}>
      {children}
    </AppChrome>
  );
}
