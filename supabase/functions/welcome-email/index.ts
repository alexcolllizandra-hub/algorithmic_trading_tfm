// Welcome email, sent once per account via Resend.
//
// Triggered by a Database Webhook on `auth.users` (INSERT + UPDATE). Deploy with
// `--no-verify-jwt`, because the webhook does not carry a user JWT.
//
// Anti-duplication is the whole difficulty here. The webhook fires on every
// update to the row, so the function sends only on the transition into a
// confirmed state: an INSERT that is already confirmed (when email confirmation
// is disabled), or an UPDATE where a confirmation timestamp goes from empty to
// set. Everything else returns 200 with `skipped`, so the webhook is not retried.

const RESEND_ENDPOINT = "https://api.resend.com/emails";
const FALLBACK_FROM = "Alx Systems <onboarding@resend.dev>";

interface AuthUserRecord {
  email?: string | null;
  email_confirmed_at?: string | null;
  confirmed_at?: string | null;
  raw_user_meta_data?: { full_name?: string | null } | null;
}

interface WebhookPayload {
  type?: "INSERT" | "UPDATE" | "DELETE";
  record?: AuthUserRecord | null;
  old_record?: AuthUserRecord | null;
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function isConfirmed(record: AuthUserRecord | null | undefined): boolean {
  return Boolean(record?.email_confirmed_at || record?.confirmed_at);
}

/** Only the transition into a confirmed state should send an email. */
function shouldSend(payload: WebhookPayload): boolean {
  const { type, record, old_record: oldRecord } = payload;
  if (!record?.email) return false;
  if (type === "INSERT") return isConfirmed(record);
  if (type === "UPDATE") return !isConfirmed(oldRecord) && isConfirmed(record);
  return false;
}

function renderHtml(name: string): string {
  const greeting = name ? `Hola ${name},` : "Hola,";
  return `<!doctype html>
<html lang="es">
  <body style="margin:0;padding:0;background:#ffffff;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;">
      <tr>
        <td align="center" style="padding:40px 16px;">
          <table role="presentation" width="560" cellpadding="0" cellspacing="0"
                 style="width:560px;max-width:100%;font-family:'Helvetica Neue',Arial,sans-serif;">
            <tr>
              <td style="padding-bottom:28px;">
                <span style="font-size:20px;font-weight:700;color:#0B1220;">Alx</span>
                <span style="font-size:12px;letter-spacing:3px;color:#5A6675;margin-left:6px;">SYSTEMS</span>
              </td>
            </tr>
            <tr>
              <td style="font-size:22px;line-height:1.35;font-weight:600;color:#0B1220;padding-bottom:16px;">
                ${greeting} tu cuenta ya está activa.
              </td>
            </tr>
            <tr>
              <td style="font-size:15px;line-height:1.65;color:#5A6675;padding-bottom:14px;">
                Esto es un laboratorio de investigación sobre estrategias de trading algorítmico,
                no un producto para operar. Todo lo que se publica se puede reproducir desde el
                código, incluidos los resultados negativos &mdash; que son la mayoría.
              </td>
            </tr>
            <tr>
              <td style="font-size:15px;line-height:1.65;color:#5A6675;padding-bottom:28px;">
                Si es tu primera visita, empieza por la sección que explica por qué casi todos los
                backtests que circulan por ahí no significan nada.
              </td>
            </tr>
            <tr>
              <td style="padding-bottom:32px;">
                <a href="https://quantivelasystems.com/#sobreajuste"
                   style="display:inline-block;background:#0EA66B;color:#ffffff;text-decoration:none;
                          font-size:15px;font-weight:600;padding:13px 26px;border-radius:6px;">
                  Ver el estudio
                </a>
              </td>
            </tr>
            <tr>
              <td style="border-top:1px solid #E7EAF1;padding-top:20px;font-size:12px;
                         line-height:1.6;color:#8A94A6;">
                Alx Systems es una plataforma tecnológica para construir y validar estrategias de
                trading algorítmico. No somos un bróker ni un asesor financiero. Operar conlleva
                riesgo de pérdida. &copy; 2026 Alx Systems.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>`;
}

Deno.serve(async (request: Request): Promise<Response> => {
  const expectedSecret = Deno.env.get("WELCOME_HOOK_SECRET");
  if (expectedSecret && request.headers.get("x-webhook-secret") !== expectedSecret) {
    return json({ error: "unauthorised" }, 401);
  }

  let payload: WebhookPayload;
  try {
    payload = (await request.json()) as WebhookPayload;
  } catch {
    return json({ error: "invalid JSON body" }, 400);
  }

  if (!shouldSend(payload)) {
    return json({ skipped: "not a transition into a confirmed account" });
  }

  const apiKey = Deno.env.get("RESEND_API_KEY");
  if (!apiKey) {
    return json({ error: "RESEND_API_KEY is not set" }, 500);
  }

  const record = payload.record as AuthUserRecord;
  const name = (record.raw_user_meta_data?.full_name ?? "").trim();

  const response = await fetch(RESEND_ENDPOINT, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "content-type": "application/json",
    },
    body: JSON.stringify({
      from: Deno.env.get("WELCOME_FROM") ?? FALLBACK_FROM,
      to: [record.email],
      subject: "Bienvenido a Alx Systems",
      html: renderHtml(name),
    }),
  });

  if (!response.ok) {
    return json({ error: "resend rejected the message", detail: await response.text() }, 502);
  }

  return json({ sent: true });
});
