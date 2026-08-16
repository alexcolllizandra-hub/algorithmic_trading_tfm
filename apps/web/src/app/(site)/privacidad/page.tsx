import type { Metadata } from "next";
import Link from "next/link";

import {
  DATA_CONTROLLER,
  PRIVACY_CONTACT,
  PRIVACY_POLICY_READY,
  PROCESSORS,
  SUPERVISORY_AUTHORITY,
} from "@/lib/legal";

export const metadata: Metadata = {
  title: "Privacidad",
  description:
    "Qué datos personales recoge Alx Systems al crear una cuenta, con qué finalidad, " +
    "quién los trata y cómo ejercer tus derechos.",
  robots: { index: true, follow: true },
};

function Block({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-border pt-8">
      <p className="rule-label text-accent">Apartado {n}</p>
      <h2 className="mt-3 text-xl font-semibold tracking-tight">{title}</h2>
      <div className="mt-4 space-y-4 leading-relaxed text-muted">{children}</div>
    </section>
  );
}

export default function PrivacidadPage() {
  return (
    <div className="mx-auto w-full max-w-3xl px-6 py-20 md:py-28">
      <p className="rule-label text-accent">Información legal</p>
      <h1 className="mt-4 text-balance text-3xl font-semibold tracking-tight md:text-4xl">
        Política de privacidad
      </h1>
      <p className="mt-5 text-pretty text-lg leading-relaxed text-muted">
        La investigación de este sitio es pública y se puede leer entera sin cuenta. Los datos
        personales solo aparecen si decides registrarte, y esto es todo lo que ocurre cuando lo
        haces.
      </p>

      {!PRIVACY_POLICY_READY && (
        <div className="mt-10 rounded-card border border-warn/40 bg-warn/5 p-6">
          <p className="rule-label text-warn">Borrador sin publicar</p>
          <h2 className="mt-3 text-lg font-semibold tracking-tight">
            Faltan el responsable del tratamiento y la dirección de contacto
          </h2>
          <p className="mt-3 leading-relaxed text-muted">
            Mientras esos dos datos no consten, este texto no es una política de privacidad válida.
            Por eso{" "}
            <strong className="font-medium text-fg">el registro de cuentas está desactivado</strong>{" "}
            y el sitio no recoge ningún dato personal. Se completan en{" "}
            <code className="font-mono text-xs text-accent">apps/web/src/lib/legal.ts</code>.
          </p>
        </div>
      )}

      <div className="mt-12 space-y-10">
        <Block n={1} title="Quién trata tus datos">
          {PRIVACY_POLICY_READY ? (
            <>
              <p>
                Responsable del tratamiento:{" "}
                <strong className="font-medium text-fg">{DATA_CONTROLLER}</strong>.
              </p>
              <p>
                Contacto para cualquier cuestión relacionada con tus datos:{" "}
                <a href={`mailto:${PRIVACY_CONTACT}`} className="text-accent hover:underline">
                  {PRIVACY_CONTACT}
                </a>
                .
              </p>
            </>
          ) : (
            <p className="text-warn">
              Pendiente de completar. Sin este apartado no se recoge ningún dato.
            </p>
          )}
        </Block>

        <Block n={2} title="Qué datos se recogen">
          <p>Únicamente los que escribes en el formulario de registro:</p>
          <ul className="list-disc space-y-2 pl-5">
            <li>
              <strong className="font-medium text-fg">Correo electrónico.</strong> Identifica la
              cuenta y es donde se envían la confirmación y la recuperación de contraseña.
            </li>
            <li>
              <strong className="font-medium text-fg">Nombre.</strong> Opcional. Solo se usa para
              encabezar los correos.
            </li>
            <li>
              <strong className="font-medium text-fg">Contraseña.</strong> Nunca se almacena en
              claro: se guarda cifrada y no es legible ni para quien administra el sitio.
            </li>
          </ul>
          <p>
            Además se instala una cookie de sesión, imprescindible para mantenerte identificado
            entre páginas. No hay cookies de analítica, de publicidad ni de terceros, y por eso no
            verás ningún banner de consentimiento.
          </p>
          <p>
            No se recogen datos de navegación con fines de perfilado, ni datos de categorías
            especiales, ni información financiera de ningún tipo. Este sitio no ejecuta operaciones
            ni se conecta a tu bróker.
          </p>
        </Block>

        <Block n={3} title="Para qué se usan">
          <ul className="list-disc space-y-2 pl-5">
            <li>
              <strong className="font-medium text-fg">Gestionar la lista de acceso</strong> a la
              plataforma: dar de alta tu cuenta y permitirte entrar al panel de investigación.
            </li>
            <li>
              <strong className="font-medium text-fg">
                Enviarte la comunicación de bienvenida
              </strong>{" "}
              y los correos imprescindibles para que la cuenta funcione: confirmación del alta y, si
              lo pides tú, recuperación de contraseña.
            </li>
          </ul>
          <p>
            No se envían boletines ni comunicaciones comerciales, no se cede ni se vende ningún dato
            a terceros, y no se toman decisiones automatizadas sobre ti.
          </p>
        </Block>

        <Block n={4} title="Con qué base legal">
          <p>
            El tratamiento se apoya en tu{" "}
            <strong className="font-medium text-fg">consentimiento</strong> (art. 6.1.a RGPD), que
            prestas al enviar el formulario de registro.
          </p>
          <p>
            Puedes <strong className="font-medium text-fg">retirarlo en cualquier momento</strong> y
            con la misma facilidad con la que lo diste, escribiendo a la dirección del apartado 7.
            Retirarlo no afecta a la licitud del tratamiento anterior a la retirada.
          </p>
          <p>
            Facilitar los datos es voluntario. Si no te registras, sigues teniendo acceso completo a
            toda la investigación publicada.
          </p>
        </Block>

        <Block n={5} title="Quién más los procesa">
          <p>
            Para funcionar, el sitio se apoya en dos proveedores que actúan como encargados del
            tratamiento y solo pueden usar los datos para prestar su servicio:
          </p>
          <ul className="space-y-4">
            {PROCESSORS.map((p) => (
              <li key={p.name} className="rounded-md border border-border bg-surface-2 p-4">
                <p className="font-medium text-fg">{p.name}</p>
                <p className="mt-1.5 text-sm leading-relaxed">{p.role}</p>
                <p className="mt-1.5 text-sm leading-relaxed">{p.location}</p>
                <a
                  href={p.url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-block text-sm text-accent hover:underline"
                >
                  Su política de privacidad
                </a>
              </li>
            ))}
          </ul>
        </Block>

        <Block n={6} title="Cuánto tiempo se conservan">
          <p>
            Mientras la cuenta siga existiendo. Si la eliminas o pides que se elimine, los datos se
            borran de forma efectiva en un plazo máximo de 30 días, salvo que alguna obligación
            legal exija conservarlos más tiempo.
          </p>
          <p>
            Los registros técnicos de envío de correo que guarda el proveedor se retienen según su
            propia política, enlazada en el apartado anterior.
          </p>
        </Block>

        <Block n={7} title="Qué derechos tienes">
          <p>
            Puedes ejercer en cualquier momento los derechos de{" "}
            <strong className="font-medium text-fg">
              acceso, rectificación, supresión y oposición
            </strong>
            , además de los de limitación del tratamiento, portabilidad y retirada del
            consentimiento.
          </p>
          {PRIVACY_POLICY_READY ? (
            <p>
              Escribe a{" "}
              <a href={`mailto:${PRIVACY_CONTACT}`} className="text-accent hover:underline">
                {PRIVACY_CONTACT}
              </a>{" "}
              indicando qué derecho quieres ejercer. La solicitud se responde en el plazo máximo de
              un mes.
            </p>
          ) : (
            <p className="text-warn">Dirección de contacto pendiente de completar.</p>
          )}
          <p>
            Si consideras que el tratamiento no se ajusta a la normativa, puedes reclamar ante la{" "}
            <a
              href={SUPERVISORY_AUTHORITY.url}
              target="_blank"
              rel="noreferrer"
              className="text-accent hover:underline"
            >
              {SUPERVISORY_AUTHORITY.name}
            </a>
            .
          </p>
        </Block>

        <Block n={8} title="Cambios en esta política">
          <p>
            Cualquier modificación se publica en esta misma página. El historial de cambios es
            público en el repositorio del proyecto, así que puedes comprobar qué cambió y cuándo sin
            depender de que te lo contemos.
          </p>
        </Block>
      </div>

      <p className="mt-14 border-t border-border pt-8 text-center text-sm text-muted">
        <Link href="/" className="underline-offset-4 hover:text-accent hover:underline">
          Volver a la investigación
        </Link>
      </p>
    </div>
  );
}
