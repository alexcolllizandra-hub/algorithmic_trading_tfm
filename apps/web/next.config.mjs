/** @type {import('next').NextConfig} */

const nextConfig = {

  reactStrictMode: true,

  output: "standalone",

  eslint: {

    ignoreDuringBuilds: true,

  },

  async redirects() {

    return [

      { source: "/market", destination: "/datos-eda", permanent: true },

      { source: "/strategy-lab", destination: "/metodologia", permanent: true },

      { source: "/experiments", destination: "/experimentos", permanent: true },

      { source: "/experiments/:runId", destination: "/experimentos?run=:runId", permanent: true },

      { source: "/performance", destination: "/resultados", permanent: true },

      { source: "/artifacts", destination: "/diagnostico", permanent: true },

      { source: "/system", destination: "/diagnostico?tab=system", permanent: true },

      { source: "/analytics", destination: "/experimentos?tab=analytics", permanent: true },

      { source: "/estudio", destination: "/resultados", permanent: true },

    ];

  },

};



export default nextConfig;

