import { DeliveryCards } from "@/components/delivery/DeliveryCards";
import { getPulse } from "@/lib/pulse";

export default async function DeliveryPage() {
  const pulse = await getPulse();
  return <DeliveryCards pulse={pulse} />;
}
