import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { logout } from "../login/actions";
import { getUserContext } from "@/lib/auth/roles";

export default async function NoAccessPage() {
  const ctx = await getUserContext();
  return (
    <main className="flex min-h-svh items-center justify-center p-6">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Account pending access</CardTitle>
          <CardDescription>
            Your account exists but no roles are assigned yet. Ask an admin to grant access.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 text-sm">
          <div>
            <p className="font-mono text-muted-foreground">Signed in as:</p>
            <p>{ctx?.email}</p>
            <p className="mt-2 font-mono text-muted-foreground">User ID:</p>
            <p className="break-all font-mono text-xs">{ctx?.userId}</p>
          </div>
          <form action={logout}>
            <Button variant="outline" type="submit">
              Sign out
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
