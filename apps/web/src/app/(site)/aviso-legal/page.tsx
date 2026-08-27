import type { Metadata } from "next";
import Link from "next/link";

import { DATA_CONTROLLER, PRIVACY_CONTACT } from "@/lib/legal";

export const metadata: Metadata = {
  title: "Aviso legal",
  description:
    "Alx Systems publica investigación con fines educativos e informativos. No es " +
    "asesoramiento financiero ni una recomendación de inversión.",
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

export default function AvisoLegalPage() {
  return (
    <div className="mx-auto w-full max-w-3xl px-6 py-20 md:py-28">
      <p className="rule-label text-accent">Información legal</p>
      <h1 className="mt-4 text-balance text-3xl font-semibold tracking-tight md:text-4xl">
        Aviso legal y descargo de responsabilidad
      </h1>
      <p className="mt-5 text-pretty text-lg leading-relaxed text-muted">
        Este sitio publica el trabajo de un laboratorio de investigación. No vende nada, no gestiona
        dinero de nadie y no dice a nadie qué comprar.
      </p>

      <div className="mt-10 rounded-card border border-warn/40 bg-warn/5 p-6">
        <p className="rule-label text-warn">Lo importante, primero</p>
        <p className="mt-3 leading-relaxed text-fg">
          Todo el contenido de esta web —el estudio, las estrategias descritas, el simulador de
          cuentas fondeadas y cualquier cifra que aparezca en cualquier página— tiene{" "}
          <strong className="font-semibold">fines exclusivamente educativos e informativos</strong>.
          No constituye asesoramiento financiero ni de inversión, ni una recomendación de compra o
          venta de ningún instrumento.
        </p>
      </div>

      <div className="mt-12 space-y-10">
        <Block n={1} title="Quién publica este sitio">
          <p>
            Responsable:{" "}
            <strong className="font-medium text-fg">{DATA_CONTROLLER ?? "pendiente"}</strong>.
            Contacto:{" "}
            {PRIVACY_CONTACT ? (
              <a href={`mailto:${PRIVACY_CONTACT}`} className="text-accent hover:underline">
                {PRIVACY_CONTACT}
              </a>
            ) : (
              "pendiente"
            )}
            .
          </p>
          <p>
            Este proyecto nace como Trabajo de Fin de Máster y se publica en abierto para que
            cualquiera pueda auditarlo.
          </p>
        </Block>

        <Block n={2} title="No es asesoramiento financiero">
          <p>
            El autor{" "}
            <strong className="font-medium text-fg">no es asesor financiero registrado</strong> ni
            está autorizado para prestar servicios de inversión. Nada de lo publicado aquí debe
            interpretarse como una recomendación personalizada.
          </p>
          <p>
            El contenido no tiene en cuenta tu situación financiera, tus objetivos ni tu tolerancia
            al riesgo, porque no los conoce. Si necesitas asesoramiento, búscalo en un profesional
            debidamente registrado ante el organismo supervisor que te corresponda.
          </p>
        </Block>

        <Block n={3} title="El riesgo de los derivados">
          <p>
            Este trabajo estudia <strong className="font-medium text-fg">futuros perpetuos</strong>,
            que son productos derivados apalancados. Operarlos conlleva un{" "}
            <strong className="font-medium text-fg">alto riesgo de pérdida</strong>, que puede
            alcanzar la totalidad del capital empleado y producirse con gran rapidez.
          </p>
          <p>
            La mayoría de las cuentas minoristas que operan estos productos pierden dinero. Nada de
            lo que leas aquí reduce ese riesgo.
          </p>
        </Block>

        <Block n={4} title="Resultados pasados y simulaciones">
          <p>
            <strong className="font-medium text-fg">
              Las rentabilidades o simulaciones pasadas no garantizan resultados futuros.
            </strong>{" "}
            Esta advertencia no es una fórmula de cortesía: es, literalmente, el hallazgo central de
            este estudio. Trece familias de estrategias fueron evaluadas y ninguna sobrevivió a la
            corrección estadística.
          </p>
          <p>
            Los resultados que se publican proceden de backtests sobre datos históricos. Un backtest
            no es un historial de operaciones reales: no soporta deslizamiento imprevisto, fallos de
            ejecución, cortes de liquidez ni las decisiones que toma una persona bajo pérdidas.
          </p>
        </Block>

        <Block n={5} title="Sobre el simulador">
          <p>
            El simulador de cuentas fondeadas es una{" "}
            <strong className="font-medium text-fg">
              herramienta didáctica que opera sobre datos simulados
            </strong>
            . No es una predicción, ni una estimación de lo que le ocurrirá a ninguna persona
            concreta, ni una valoración de ninguna empresa de fondeo real.
          </p>
          <p>
            Sirve para enseñar una idea —que el azar produce resultados que parecen destreza— y para
            nada más. Sus cifras son inventadas por construcción y así se indica en cada gráfico.
          </p>
        </Block>

        <Block n={6} title="Limitación de responsabilidad">
          <p>
            El contenido se ofrece <em>tal cual</em>, sin garantía de exactitud, integridad ni
            vigencia. El autor no asume responsabilidad por decisiones de inversión tomadas a partir
            de este material, ni por pérdidas directas o indirectas derivadas de su uso.
          </p>
          <p>
            Si detectas un error metodológico o factual, comunicarlo es la contribución más útil
            posible: el repositorio es público y acepta issues.
          </p>
        </Block>

        <Block n={7} title="Propiedad intelectual">
          <p>
            El código se publica bajo licencia MIT. Los textos y figuras pueden citarse indicando la
            fuente y el enlace al repositorio original.
          </p>
        </Block>
      </div>

      <div className="mt-14 border-t border-border pt-8">
        <p className="text-sm text-muted">
          Consulta también la{" "}
          <Link href="/privacidad" className="text-accent underline-offset-4 hover:underline">
            política de privacidad
          </Link>
          .
        </p>
        <p className="mt-4 text-center text-sm text-muted">
          <Link href="/" className="underline-offset-4 hover:text-accent hover:underline">
            Volver a la investigación
          </Link>
        </p>
      </div>
    </div>
  );
}
