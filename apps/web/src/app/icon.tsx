// Browser-tab icon, generated at build time — no binary in the repository.
//
// The mark is the rotated diamond the header uses (◈), drawn as two nested
// squares rather than as the glyph: Satori only ships Latin coverage, so a
// geometric shape renders identically everywhere while a unicode symbol would
// risk a blank tile.

import { ImageResponse } from "next/og";

// Edge runtime: on the Node runtime under Windows, @vercel/og resolves its
// bundled font through fileURLToPath on a malformed path and the route 500s.
export const runtime = "edge";

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

const GROUND = "#0D1117";
const ACCENT = "#2DD4BF";

export default function Icon() {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: GROUND,
      }}
    >
      <div
        style={{
          width: 19,
          height: 19,
          background: ACCENT,
          transform: "rotate(45deg)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div style={{ width: 7, height: 7, background: GROUND }} />
      </div>
    </div>,
    { ...size }
  );
}
