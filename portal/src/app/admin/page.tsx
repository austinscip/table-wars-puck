import { createClient } from "@/lib/supabase/server";
import { requireSuperAdmin } from "@/lib/auth/roles";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default async function AdminDashboard() {
  // Authorize at the data-access layer, not just the layout (layouts don't
  // re-run on every navigation). No extra DB cost — getUserContext is cached.
  await requireSuperAdmin();
  const supabase = await createClient();

  const [
    { data: tenants },
    { data: organizations },
    { data: locations },
    { data: pucks },
    { data: tvs },
    { data: firmware },
    { data: recentMatches },
    { count: totalMatches },
    { count: activeMatches },
  ] = await Promise.all([
    supabase.from("tenants").select("id, name, slug, status, created_at"),
    supabase.from("organizations").select("id, name, tenant_id"),
    supabase
      .from("locations")
      .select("id, name, city, state, is_active, table_count, organization_id"),
    supabase
      .from("pucks")
      .select("id, serial_no, hw_revision, puck_index, battery_pct, is_online, last_seen, current_firmware_id")
      .order("last_seen", { ascending: false, nullsFirst: false })
      .limit(50),
    supabase
      .from("tvs")
      .select("id, device_name, table_number, app_version, storage_free_kb, is_online, last_seen, location_id")
      .order("last_seen", { ascending: false, nullsFirst: false })
      .limit(50),
    supabase
      .from("firmware_versions")
      .select("id, version, channel, hw_revision, released_at")
      .order("released_at", { ascending: false })
      .limit(10),
    // Recent activity — what's actually being played (joins the game name +
    // venue). The per-game analytics live in PostHog (server-side); this is the
    // operational at-a-glance for the fleet.
    supabase
      .from("matches")
      .select("id, status, table_number, started_at, ended_at, player_count, games(slug, display_name), locations(name)")
      .order("started_at", { ascending: false })
      .limit(15),
    supabase.from("matches").select("id", { count: "exact", head: true }),
    supabase
      .from("matches")
      .select("id", { count: "exact", head: true })
      .eq("status", "active"),
  ]);

  // Fleet-health signals — turn the raw rows into the handful of numbers that
  // actually need attention (Mike's "watch the pucks + the TV storage").
  const offlinePucks = (pucks ?? []).filter((p) => !p.is_online).length;
  const lowBatteryPucks = (pucks ?? []).filter(
    (p) => p.battery_pct != null && p.battery_pct < 25,
  ).length;
  const lowStorageTvs = (tvs ?? []).filter(
    (tv) => tv.storage_free_kb != null && tv.storage_free_kb < 50_000,
  ).length;
  // Embedded relations come back loosely typed without generated DB types;
  // normalise object-or-array for the game/venue name.
  const gameName = (m: { games?: unknown }) => {
    const g = m.games as { display_name?: string } | { display_name?: string }[] | null;
    return (Array.isArray(g) ? g[0]?.display_name : g?.display_name) ?? "—";
  };
  const venueName = (m: { locations?: unknown }) => {
    const l = m.locations as { name?: string } | { name?: string }[] | null;
    return (Array.isArray(l) ? l[0]?.name : l?.name) ?? "—";
  };

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-semibold">Super-admin observability</h1>
        <p className="text-sm text-muted-foreground">Fleet-wide drill-down.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Tenants</CardDescription>
            <CardTitle className="text-3xl">{tenants?.length ?? 0}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Organizations</CardDescription>
            <CardTitle className="text-3xl">{organizations?.length ?? 0}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Locations</CardDescription>
            <CardTitle className="text-3xl">{locations?.length ?? 0}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Pucks</CardDescription>
            <CardTitle className="text-3xl">{pucks?.length ?? 0}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Fleet health — the numbers that need attention, not raw counts. */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Fleet health</CardTitle>
          <CardDescription>What needs attention right now.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-4">
            <HealthStat label="Pucks offline" value={offlinePucks} alert={offlinePucks > 0} />
            <HealthStat label="Low battery (<25%)" value={lowBatteryPucks} alert={lowBatteryPucks > 0} />
            <HealthStat label="TVs low storage" value={lowStorageTvs} alert={lowStorageTvs > 0} />
            <HealthStat label="Matches live now" value={activeMatches ?? 0} alert={false} />
          </div>
        </CardContent>
      </Card>

      {/* Live activity — what's actually being played across the fleet. */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent matches</CardTitle>
          <CardDescription>
            {(totalMatches ?? 0).toLocaleString()} total · {activeMatches ?? 0} live
          </CardDescription>
        </CardHeader>
        <CardContent>
          {recentMatches && recentMatches.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Game</TableHead>
                  <TableHead>Venue</TableHead>
                  <TableHead>Table</TableHead>
                  <TableHead>Players</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Started</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentMatches.map((m) => (
                  <TableRow key={m.id}>
                    <TableCell>{gameName(m)}</TableCell>
                    <TableCell>{venueName(m)}</TableCell>
                    <TableCell>{m.table_number ?? "—"}</TableCell>
                    <TableCell>{m.player_count}</TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          m.status === "active"
                            ? "default"
                            : m.status === "finished"
                              ? "secondary"
                              : "outline"
                        }
                      >
                        {m.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(m.started_at).toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground">No matches played yet.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Tenants</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Slug</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tenants?.map((t) => (
                <TableRow key={t.id}>
                  <TableCell>{t.name}</TableCell>
                  <TableCell className="font-mono text-xs">{t.slug}</TableCell>
                  <TableCell>
                    <Badge variant={t.status === "active" ? "default" : "secondary"}>{t.status}</Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(t.created_at).toLocaleDateString()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Pucks (most recent activity)</CardTitle>
        </CardHeader>
        <CardContent>
          {pucks && pucks.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>#</TableHead>
                  <TableHead>Serial</TableHead>
                  <TableHead>HW</TableHead>
                  <TableHead>Battery</TableHead>
                  <TableHead>Online</TableHead>
                  <TableHead>Last seen</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pucks.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell>{p.puck_index}</TableCell>
                    <TableCell className="font-mono text-xs">{p.serial_no}</TableCell>
                    <TableCell>{p.hw_revision}</TableCell>
                    <TableCell>
                      <span className={p.battery_pct != null && p.battery_pct < 25 ? "text-red-600" : ""}>
                        {p.battery_pct != null ? `${p.battery_pct}%` : "—"}
                      </span>
                    </TableCell>
                    <TableCell>
                      <Badge variant={p.is_online ? "default" : "secondary"}>
                        {p.is_online ? "online" : "offline"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {p.last_seen ? new Date(p.last_seen).toLocaleString() : "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground">No pucks registered yet.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">TVs</CardTitle>
          <CardDescription>
            Watch for low storage — out-of-memory crashes games (Mike&apos;s &quot;nine kilobytes free&quot; example).
          </CardDescription>
        </CardHeader>
        <CardContent>
          {tvs && tvs.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Device</TableHead>
                  <TableHead>Table</TableHead>
                  <TableHead>App version</TableHead>
                  <TableHead>Storage free</TableHead>
                  <TableHead>Online</TableHead>
                  <TableHead>Last seen</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tvs.map((tv) => (
                  <TableRow key={tv.id}>
                    <TableCell>{tv.device_name}</TableCell>
                    <TableCell>{tv.table_number ?? "—"}</TableCell>
                    <TableCell className="font-mono text-xs">{tv.app_version ?? "—"}</TableCell>
                    <TableCell>
                      <span className={tv.storage_free_kb != null && tv.storage_free_kb < 50_000 ? "text-red-600" : ""}>
                        {tv.storage_free_kb != null ? `${(tv.storage_free_kb / 1024).toFixed(1)} MB` : "—"}
                      </span>
                    </TableCell>
                    <TableCell>
                      <Badge variant={tv.is_online ? "default" : "secondary"}>
                        {tv.is_online ? "online" : "offline"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {tv.last_seen ? new Date(tv.last_seen).toLocaleString() : "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground">No TVs registered yet.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Firmware versions</CardTitle>
        </CardHeader>
        <CardContent>
          {firmware && firmware.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Version</TableHead>
                  <TableHead>HW</TableHead>
                  <TableHead>Channel</TableHead>
                  <TableHead>Released</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {firmware.map((f) => (
                  <TableRow key={f.id}>
                    <TableCell className="font-mono text-xs">{f.version}</TableCell>
                    <TableCell>{f.hw_revision}</TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          f.channel === "stable" ? "default" : f.channel === "beta" ? "secondary" : "outline"
                        }
                      >
                        {f.channel}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(f.released_at).toLocaleDateString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground">No firmware versions registered yet.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function HealthStat({ label, value, alert }: { label: string; value: number; alert: boolean }) {
  return (
    <div className="rounded-lg border p-3">
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className={`text-2xl font-semibold ${alert ? "text-red-600" : ""}`}>{value}</div>
    </div>
  );
}
