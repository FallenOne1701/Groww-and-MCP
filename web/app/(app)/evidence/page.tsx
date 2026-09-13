import { EvidenceBoard } from "@/components/evidence/EvidenceBoard";
import { getPulse } from "@/lib/pulse";
import type { ThemeId } from "@/lib/types";

const THEME_IDS = new Set<ThemeId>([
  "app_reliability",
  "trading_orders",
  "customer_support",
  "fees_funding",
  "charts_market_data",
]);

export default async function EvidencePage({
  searchParams,
}: {
  searchParams: Promise<{ theme?: string }>;
}) {
  const pulse = await getPulse();
  const params = await searchParams;
  const theme = THEME_IDS.has(params.theme as ThemeId)
    ? (params.theme as ThemeId)
    : undefined;

  return <EvidenceBoard pulse={pulse} initialTheme={theme} />;
}
