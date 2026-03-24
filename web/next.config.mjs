/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverComponentsExternalPackages: ["mammoth", "pdf-parse"],
  },
};

export default nextConfig;
