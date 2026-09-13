import { ThemeTable } from "@/components/themes/ThemeTable";
import { getPulse } from "@/lib/pulse";

export default async function ThemesPage() {
  const pulse = await getPulse();
  return <ThemeTable pulse={pulse} />;
}
