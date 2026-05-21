"use client";
import Link from "next/link";
import { Suspense, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { claimSession } from "@/lib/session/sessionClaim";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next") ?? "/dashboard";
  const authError = searchParams.get("error");
  const reason = searchParams.get("reason");
  const [notice, setNotice] = useState<string | null>(
    reason === "signed-in-elsewhere"
      ? "You were signed out because this account signed in on another device."
      : null
  );
  const [error, setError] = useState<string | null>(
    authError === "auth_failed" ? "Google sign-in failed. Please try again." : null
  );
  const [loading, setLoading] = useState(false);
  const supabase = useMemo(() => createClient(), []);

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setNotice(null);
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      setError(error.message);
      setLoading(false);
    } else {
      if (data.user) await claimSession(supabase, data.user.id);
      router.push(next);
      router.refresh();
    }
  };

  const [googleLoading, setGoogleLoading] = useState(false);

  const handleGoogleLogin = async () => {
    setGoogleLoading(true);
    setError(null);
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`,
      },
    });
    if (error) {
      setError(error.message);
      setGoogleLoading(false);
    }
    // on success the browser is redirected — no need to reset loading
  };

  return (
    <Card className="rounded-2xl border-border shadow-2xl">
      <CardHeader className="text-center pb-2 pt-8 px-8">
        <div className="flex items-center justify-center gap-2 mb-5">
          <div className="w-2 h-2 rounded-full bg-primary" />
          <span className="font-display font-bold text-base">TradeDash</span>
        </div>
        <CardTitle className="font-display text-xl">Welcome back</CardTitle>
        <CardDescription className="text-sm">Sign in to your account</CardDescription>
      </CardHeader>
      <CardContent className="px-8 pb-8 pt-6 space-y-4">
        <Button
          type="button"
          variant="outline"
          className="w-full rounded-xl border-border h-11 text-sm font-medium"
          onClick={handleGoogleLogin}
          disabled={googleLoading}
        >
          <svg className="mr-2.5 h-4 w-4" viewBox="0 0 24 24">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
          </svg>
          {googleLoading ? "Redirecting…" : "Continue with Google"}
        </Button>

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t border-border" />
          </div>
          <div className="relative flex justify-center text-xs">
            <span className="bg-card px-2 text-muted-foreground uppercase tracking-wider">or</span>
          </div>
        </div>

        <form onSubmit={handleEmailLogin} className="space-y-4">
          {notice && (
            <div className="text-xs text-amber-600 dark:text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
              {notice}
            </div>
          )}
          {error && (
            <div className="text-xs text-destructive bg-destructive/10 border border-destructive/20 rounded-lg px-3 py-2">
              {error}
            </div>
          )}
          <div className="space-y-1.5">
            <Label htmlFor="email" className="text-xs text-muted-foreground">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="rounded-xl h-11 border-border bg-muted/30"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password" className="text-xs text-muted-foreground">Password</Label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="rounded-xl h-11 border-border bg-muted/30"
            />
          </div>
          <Button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl h-11 bg-primary hover:bg-primary/90 font-medium"
          >
            {loading ? "Signing in…" : "Sign In"}
          </Button>
        </form>

        <p className="text-center text-xs text-muted-foreground pt-1">
          No account?{" "}
          <Link href="/signup" className="text-primary hover:underline">Sign up free</Link>
        </p>
      </CardContent>
    </Card>
  );
}

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-6">
          <Link href="/" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            ← TradeDash
          </Link>
        </div>
        <Suspense fallback={<div className="h-96 rounded-2xl border border-border animate-pulse bg-muted/20" />}>
          <LoginForm />
        </Suspense>
      </div>
    </main>
  );
}
