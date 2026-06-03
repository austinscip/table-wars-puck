import { redirect } from "next/navigation";
import { getUserContext } from "@/lib/auth/roles";

export default async function Home() {
  const ctx = await getUserContext();
  if (!ctx) redirect("/login");
  if (ctx.isSuperAdmin) redirect("/admin");
  if (ctx.hasAnyRole) redirect("/bar");
  redirect("/no-access");
}
