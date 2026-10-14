import { PositionDetail } from "@/components/position-detail";
export default async function Page({
  params,
}: {
  params: Promise<{ storeId: string; productId: string }>;
}) {
  const ids = await params;
  return <PositionDetail {...ids} />;
}
