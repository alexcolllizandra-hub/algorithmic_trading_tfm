// Server-side Supabase client for Server Components and Route Handlers.
//
// Reads the session from the request cookies so a server render knows who is
// signed in. Still uses the anon key: row-level security is the authority on
// what a user may read, and the service-role key never enters this app.

import { createServerClient, type CookieOptions } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";
import { cookies } from "next/headers";

type CookieToSet = { name: string; value: string; options: CookieOptions };

export function isAuthConfiguredServer(): boolean {
  return Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY);
}

export function getSupabaseServerClient(): SupabaseClient | null {
  if (!isAuthConfiguredServer()) return null;
  const cookieStore = cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL as string,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY as string,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet: CookieToSet[]) {
          // Server Components cannot write cookies; the middleware refreshes the
          // session instead. Swallowing here is the documented Supabase pattern.
          try {
            cookiesToSet.forEach(({ name, value, options }) => {
              cookieStore.set(name, value, options);
            });
          } catch {
            // No-op: called from a Server Component render.
          }
        },
      },
    }
  );
}

/** The signed-in user for this request, or null. */
export async function getCurrentUser() {
  const supabase = getSupabaseServerClient();
  if (!supabase) return null;
  const {
    data: { user },
  } = await supabase.auth.getUser();
  return user;
}
