import type { NextConfig } from "next";

// Security headers for an internet-facing, auth-bearing admin panel. We keep
// CSP minimal — `frame-ancestors 'none'` (anti-clickjacking) only — rather than
// a full script-src policy, which on Next.js needs per-request nonces and would
// otherwise break the framework's inline bootstrap + the Supabase client. The
// framing/sniffing/referrer headers below are safe blanket hardening.
// (audit portal-2026-06-06)
const securityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Content-Security-Policy", value: "frame-ancestors 'none'" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=()",
  },
];

const nextConfig: NextConfig = {
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
