import { SupplierDetail } from "@/components/supplier-pages";
export default async function Page({
  params,
}: {
  params: Promise<{ supplierId: string }>;
}) {
  return <SupplierDetail id={(await params).supplierId} />;
}
