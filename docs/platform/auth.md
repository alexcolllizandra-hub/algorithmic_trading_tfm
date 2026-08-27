# Authentication and transactional email

The public research site works **without** authentication. Signing in is an
optional layer: it gates the research panel and nothing else. If a deployment
has no Supabase credentials, the sign-in button disappears, the middleware
becomes a no-op, and every page renders as before.

That is a deliberate constraint. The scientific content of this project must
stay readable by anyone, including a reviewer with no account.

---

## 1. Two independent systems

There are two separate email paths and they are configured in different places.

```
Registro (frontend)
  -> supabase.auth.signUp()
       -> Supabase Auth envía "Confirm signup"          [plantilla en el Dashboard]
       -> el usuario pulsa {{ .ConfirmationURL }}
       -> auth.users.email_confirmed_at queda relleno
            -> Database Webhook (INSERT + UPDATE)
                 -> Edge Function welcome-email          [código en este repo]
                      -> Resend -> "Bienvenido a Alx Systems"
```

Password recovery follows the same shape: `resetPasswordForEmail()` sends the
`Reset password` template, the link returns to the site's origin, and the
`PASSWORD_RECOVERY` event puts `AuthPanel` into its "choose a new password"
state.

| Concern | Lives in | Configured where |
|---|---|---|
| Confirmation and reset emails | Supabase Auth | Dashboard → Authentication → Emails → Templates |
| Welcome email | This repo | `supabase/functions/welcome-email/` |
| Session handling | This repo | `apps/web/src/lib/auth`, `apps/web/src/middleware.ts` |

---

## 2. Files in this repository

| Path | Role |
|---|---|
| `apps/web/src/lib/supabase/client.ts` | Browser client; returns `null` when unconfigured |
| `apps/web/src/lib/supabase/server.ts` | Server Components / Route Handlers |
| `apps/web/src/lib/auth/AuthContext.tsx` | Session state, sign-up / sign-in / reset, Spanish error messages |
| `apps/web/src/components/auth/AuthPanel.tsx` | The single form: entrar, crear cuenta, recuperar |
| `apps/web/src/app/acceso/page.tsx` | Public route `/acceso` (noindex) |
| `apps/web/src/middleware.ts` | Refreshes the session; redirects `/panel` when signed out |
| `supabase/functions/welcome-email/index.ts` | Deno Edge Function, sends via Resend |
| `supabase/templates/confirm-signup.html` | Auth template — paste into the Dashboard |
| `supabase/templates/reset-password.html` | Auth template — paste into the Dashboard |

---

## 3. Environment

The web app needs exactly two variables, both safe for the browser:

```bash
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
```

```bash
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key>
```

> **The service-role key must never appear in `apps/web`.** It bypasses row-level
> security. It belongs only to the Python side (`SUPABASE_SERVICE_ROLE_KEY`),
> which uses it for object storage and never ships it to a client.

---

## 4. Deploying the welcome email

Load the function's secrets:

```bash
supabase secrets set --env-file ./supabase/functions/welcome-email/.env
```

Deploy without JWT verification, because a database webhook carries no user JWT:

```bash
supabase functions deploy welcome-email --no-verify-jwt
```

Then create the webhook in **Dashboard → Database → Webhooks**:

- Table: `auth.users`
- Events: `INSERT` and `UPDATE`
- URL: `https://<project-ref>.supabase.co/functions/v1/welcome-email`
- Optional header: `x-webhook-secret` matching `WELCOME_HOOK_SECRET`

The function only sends on the **transition into a confirmed account**, so the
repeated UPDATE events a normal session generates return `200 {"skipped": …}`
rather than emailing the user again.

---

## 5. Sender domain

Without a verified domain, Resend only delivers to the address that owns the
Resend account, and `WELCOME_FROM` must be `onboarding@resend.dev`. With a
verified domain (SPF, DKIM and DMARC records in DNS), any recipient works.

To make the **confirmation and reset** emails come from the same address, set
custom SMTP in Dashboard → Authentication → Emails:

- host `smtp.resend.com`, user `resend`, password = the Resend API key.

---

## 6. Checklist

1. Create the Supabase project and copy the URL and anon key into the web env.
2. Verify the sending domain in Resend and add the DNS records.
3. Set the function secrets and deploy `welcome-email --no-verify-jwt`.
4. Create the `auth.users` webhook pointing at the function.
5. Paste both HTML templates into Authentication → Emails → Templates.
6. Add the site origin to Authentication → URL Configuration → Redirect URLs.
7. (Recommended) Configure custom SMTP so every email shares one sender.
8. Register a test account and confirm that exactly **one** welcome email arrives.

---

## 7. Key hygiene

API keys are credentials, not configuration. They do not belong in git, in a
chat message, in a screenshot or in an issue. If one is exposed anywhere, rotate
it in the Resend dashboard first and update the secret afterwards — rotation
costs a minute and revokes the exposure completely.
