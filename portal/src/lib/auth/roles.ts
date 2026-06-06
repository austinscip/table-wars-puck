import { cache } from "react";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export type Role = "super_admin" | "tenant_admin" | "org_admin" | "bar_manager" | "bar_staff";

export type UserContext = {
  userId: string;
  email: string;
  displayName: string | null;
  orgRoles: { organizationId: string; role: Role }[];
  locationRoles: { locationId: string; role: Role }[];
  isSuperAdmin: boolean;
  hasAnyRole: boolean;
};

// Wrapped in React `cache()` so a single request that needs the context in
// both a layout and its page (e.g. the layout gate + the page's data-access
// guard below) resolves it ONCE — the three role queries don't run twice.
// This is also the Next.js-recommended Data Access Layer shape (auth checks
// live next to the data, not only in layouts — see
// node_modules/next/dist/docs/.../data-security.md).
export const getUserContext = cache(async (): Promise<UserContext | null> => {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;

  const [{ data: profile }, { data: orgRoles }, { data: locationRoles }] = await Promise.all([
    supabase.from("users").select("display_name").eq("id", user.id).maybeSingle(),
    supabase
      .from("user_org_roles")
      .select("organization_id, role")
      .eq("user_id", user.id),
    supabase
      .from("user_location_roles")
      .select("location_id, role")
      .eq("user_id", user.id),
  ]);

  const orgs = (orgRoles ?? []).map((r) => ({
    organizationId: r.organization_id as string,
    role: r.role as Role,
  }));
  const locations = (locationRoles ?? []).map((r) => ({
    locationId: r.location_id as string,
    role: r.role as Role,
  }));

  return {
    userId: user.id,
    email: user.email ?? "",
    displayName: profile?.display_name ?? null,
    orgRoles: orgs,
    locationRoles: locations,
    isSuperAdmin: orgs.some((r) => r.role === "super_admin"),
    hasAnyRole: orgs.length > 0 || locations.length > 0,
  };
});

// Authorization guards co-located with data access. Call these at the TOP of a
// protected page/data function — NOT only in the layout. Next.js layouts don't
// re-execute on every navigation (partial rendering), so a layout-only gate is
// not a reliable security boundary; the data fetch must verify the caller too.
// These mirror the layout redirects so behaviour is identical, and return the
// context so the caller can reuse it. The cached getUserContext above means
// this adds no extra DB round-trips.

/** Require a signed-in super-admin. Redirects otherwise. Returns the context. */
export async function requireSuperAdmin(): Promise<UserContext> {
  const ctx = await getUserContext();
  if (!ctx) redirect("/login");
  if (!ctx.isSuperAdmin) redirect("/bar");
  return ctx;
}

/** Require a signed-in user with at least one role. Redirects otherwise. */
export async function requireAnyRole(): Promise<UserContext> {
  const ctx = await getUserContext();
  if (!ctx) redirect("/login");
  if (!ctx.hasAnyRole) redirect("/no-access");
  return ctx;
}
