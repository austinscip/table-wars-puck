import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { logout } from "@/app/login/actions";
import type { UserContext } from "@/lib/auth/roles";

export function AppHeader({ ctx, section }: { ctx: UserContext; section: "bar" | "admin" }) {
  return (
    <header className="border-b">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <div className="flex items-center gap-3">
          <Link href="/" className="font-semibold">
            Table Wars
          </Link>
          <Badge variant={section === "admin" ? "default" : "secondary"}>
            {section === "admin" ? "Super-admin" : "Bar portal"}
          </Badge>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-muted-foreground">{ctx.displayName ?? ctx.email}</span>
          {ctx.isSuperAdmin && section !== "admin" && (
            <Link href="/admin" className="text-sm underline">
              Admin
            </Link>
          )}
          {section === "admin" && (
            <Link href="/bar" className="text-sm underline">
              Bar view
            </Link>
          )}
          <form action={logout}>
            <Button size="sm" variant="outline" type="submit">
              Sign out
            </Button>
          </form>
        </div>
      </div>
    </header>
  );
}
