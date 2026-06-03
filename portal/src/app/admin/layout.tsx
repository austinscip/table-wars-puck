import { redirect } from "next/navigation";
import { getUserContext } from "@/lib/auth/roles";
import { AppHeader } from "@/components/app-header";

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const ctx = await getUserContext();
  if (!ctx) redirect("/login");
  if (!ctx.isSuperAdmin) redirect("/bar");

  return (
    <div className="min-h-svh">
      <AppHeader ctx={ctx} section="admin" />
      <div className="mx-auto max-w-7xl p-6">{children}</div>
    </div>
  );
}
