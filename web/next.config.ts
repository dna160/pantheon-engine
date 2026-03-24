import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    serverComponentsExternalPackages: ["mammoth", "pdf-parse"],
  },
};

export default nextConfig;
