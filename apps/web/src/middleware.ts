// Refreshes the Supabase session on every request and gates the research panel.
//
// Two things happen here that cannot happen in a Server Component: the session
// cookie is rewritten when the access token is close to expiring, and an
// unauthenticated request to a private route is redirected before any data is
// fetched.
//
// When the deployment has no Supabase credentials the middleware is a no-op, so
// the public research site keeps working with authentication switched off.

import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

type CookieToSet = { name: string; value: string; options: CookieOptions };

/** Routes that require a signed-in user. The public site is never gated. */
const PRIVATE_PREFIXES = ["/panel"];

export async function middleware(request: NextRequest) {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return NextResponse.next();

  let response = NextResponse.next({ request });

  const supabase = createServerClient(url, key, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet: CookieToSet[]) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options)
        );
      },
    },
  });

  // getUser() revalidates the token with Supabase; getSession() alone would
  // trust a cookie the client could have forged.
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const path = request.nextUrl.pathname;
  const isPrivate = PRIVATE_PREFIXES.some((p) => path === p || path.startsWith(`${p}/`));

  if (isPrivate && !user) {
    const redirect = request.nextUrl.clone();
    redirect.pathname = "/acceso";
    redirect.searchParams.set("next", path);
    return NextResponse.redirect(redirect);
  }

  return response;
}

export const config = {
  // Everything except static assets and image files.
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|data/|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
