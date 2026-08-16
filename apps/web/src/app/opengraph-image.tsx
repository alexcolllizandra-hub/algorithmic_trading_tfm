// Social preview card, generated at build time — no binary in the repository.
//
// It states the study's actual result rather than a slogan: the page it
// represents is a negative finding, and the preview should not promise anything
// the page then has to walk back.

import { ImageResponse } from "next/og";

// Edge runtime: on the Node runtime under Windows, @vercel/og resolves its
// bundled font through fileURLToPath on a malformed path and the route 500s.
export const runtime = "edge";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt =
  "Alx Systems — laboratorio de investigación reproducible sobre futuros perpetuos de BTC y ETH";

const GROUND = "#0D1117";
const SURFACE = "#131821";
const BORDER = "#212A38";
const FG = "#E6EDF3";
const MUTED = "#8B98A9";
const ACCENT = "#2DD4BF";

export default function OpengraphImage() {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        background: GROUND,
        padding: "72px 80px",
      }}
    >
      {/* Wordmark */}
      <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
        <div
          style={{
            width: 30,
            height: 30,
            background: ACCENT,
            transform: "rotate(45deg)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div style={{ width: 11, height: 11, background: GROUND }} />
        </div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
          <span style={{ fontSize: 34, fontWeight: 700, color: FG, letterSpacing: -0.5 }}>Alx</span>
          <span style={{ fontSize: 19, color: MUTED, letterSpacing: 6 }}>SYSTEMS</span>
        </div>
      </div>

      {/* Thesis */}
      <div style={{ display: "flex", flexDirection: "column", gap: 26 }}>
        <span
          style={{
            fontSize: 62,
            fontWeight: 600,
            color: FG,
            letterSpacing: -1.6,
            lineHeight: 1.12,
            maxWidth: 940,
          }}
        >
          Un laboratorio para buscar estrategias de trading y para no engañarse con ellas.
        </span>
        <span style={{ fontSize: 27, color: MUTED, lineHeight: 1.45, maxWidth: 880 }}>
          Seis años de datos reales de BTC y ETH perpetuo, validación cronológica y resultados
          negativos publicados.
        </span>
      </div>

      {/* Receipt strip */}
      <div
        style={{
          display: "flex",
          gap: 14,
          borderTop: `1px solid ${BORDER}`,
          paddingTop: 26,
        }}
      >
        {["13 familias evaluadas", "496.500 configuraciones", "0 sobreviven la corrección"].map(
          (label) => (
            <div
              key={label}
              style={{
                display: "flex",
                background: SURFACE,
                border: `1px solid ${BORDER}`,
                borderRadius: 6,
                padding: "12px 20px",
                fontSize: 23,
                color: MUTED,
              }}
            >
              {label}
            </div>
          )
        )}
      </div>
    </div>,
    { ...size }
  );
}
