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

export async function getUserContext(): Promise<UserContext | null> {
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
}
