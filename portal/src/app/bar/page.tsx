import { createClient } from "@/lib/supabase/server";
import { requireAnyRole } from "@/lib/auth/roles";
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

export default async function BarDashboard() {
  // Authorize at the data-access layer, not just the layout. No extra DB cost
  // (getUserContext is cached). Row scoping itself is enforced by RLS below.
  await requireAnyRole();
  const supabase = await createClient();

  // RLS scopes all of these to the locations the user can see.
  const [{ data: locations }, { data: activeMatches }, { data: pucks }] = await Promise.all([
    supabase.from("locations").select("id, name, city, state, table_count, is_active"),
    supabase
      .from("matches")
      .select("id, table_number, status, started_at, player_count, games(display_name)")
      .in("status", ["lobby", "active"])
      .order("started_at", { ascending: false }),
    supabase
      .from("pucks")
      .select("id, serial_no, puck_index, battery_pct, is_online, last_seen")
      .order("puck_index", { ascending: true }),
  ]);

  const onlinePucks = pucks?.filter((p) => p.is_online).length ?? 0;
  const lowBattery = pucks?.filter((p) => (p.battery_pct ?? 100) < 25).length ?? 0;

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-semibold">Bar dashboard</h1>
        <p className="text-sm text-muted-foreground">
          {locations?.[0]?.name ?? "No location"}
          {locations?.[0]?.city ? ` — ${locations[0].city}, ${locations[0].state}` : ""}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Active matches</CardDescription>
            <CardTitle className="text-3xl">{activeMatches?.length ?? 0}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Online pucks</CardDescription>
            <CardTitle className="text-3xl">
              {onlinePucks} <span className="text-base text-muted-foreground">/ {pucks?.length ?? 0}</span>
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Low battery</CardDescription>
            <CardTitle className="text-3xl">{lowBattery}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Tables</CardDescription>
            <CardTitle className="text-3xl">{locations?.[0]?.table_count ?? 0}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle className="text-base">Avg time at table</CardTitle>
            <CardDescription>vs. your 45-min baseline</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">— min</p>
            <p className="text-sm text-muted-foreground">No data yet. Pilot will populate this.</p>
          </CardContent>
        </Card>
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle className="text-base">Matches today</CardTitle>
            <CardDescription>Across all tables</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">—</p>
            <p className="text-sm text-muted-foreground">No data yet.</p>
          </CardContent>
        </Card>
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle className="text-base">Repeat players</CardTitle>
            <CardDescription>Returning within 7 days</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">—</p>
            <p className="text-sm text-muted-foreground">No data yet.</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Active matches</CardTitle>
        </CardHeader>
        <CardContent>
          {activeMatches && activeMatches.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Table</TableHead>
                  <TableHead>Game</TableHead>
                  <TableHead>Players</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Started</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {activeMatches.map((m) => (
                  <TableRow key={m.id}>
                    <TableCell>{m.table_number ?? "—"}</TableCell>
                    <TableCell>
                      {Array.isArray(m.games) ? m.games[0]?.display_name : (m.games as { display_name: string } | null)?.display_name}
                    </TableCell>
                    <TableCell>{m.player_count}</TableCell>
                    <TableCell>
                      <Badge variant={m.status === "active" ? "default" : "secondary"}>{m.status}</Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(m.started_at).toLocaleTimeString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground">No active matches right now.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Pucks</CardTitle>
          <CardDescription>Charge anything under 25%.</CardDescription>
        </CardHeader>
        <CardContent>
          {pucks && pucks.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>#</TableHead>
                  <TableHead>Serial</TableHead>
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
            <p className="text-sm text-muted-foreground">No pucks assigned to this location yet.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
