import { redirect } from "next/navigation";
import { getUserContext } from "@/lib/auth/roles";
import { AppHeader } from "@/components/app-header";

export default async function BarLayout({ children }: { children: React.ReactNode }) {
  const ctx = await getUserContext();
  if (!ctx) redirect("/login");
  if (!ctx.hasAnyRole) redirect("/no-access");

  return (
    <div className="min-h-svh">
      <AppHeader ctx={ctx} section="bar" />
      <div className="mx-auto max-w-7xl p-6">{children}</div>
    </div>
  );
}
