import { GateChecklist } from "@/components/gates/GateChecklist";
import { getPulse } from "@/lib/pulse";

export default async function GatesPage() {
  const pulse = await getPulse();
  return <GateChecklist pulse={pulse} />;
}
