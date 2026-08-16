"use client";

// Browser-side Supabase client.
//
// Only the anon key is ever used here. It is safe to ship to the browser: it
// carries no privileges beyond what row-level security grants an anonymous or
// signed-in user. The service-role key must NEVER appear in this app.

import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";

let cached: SupabaseClient | null = null;

/** True when the deployment has been given Supabase credentials. */
export function isAuthConfigured(): boolean {
  return Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY);
}

/**
 * The shared browser client, or `null` when auth is not configured.
 *
 * Returning null rather than throwing lets the public site render normally on a
 * deployment that has no Supabase project attached — the research content does
 * not depend on authentication.
 */
export function getSupabaseBrowserClient(): SupabaseClient | null {
  if (!isAuthConfigured()) return null;
  if (!cached) {
    cached = createBrowserClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL as string,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY as string
    );
  }
  return cached;
}
