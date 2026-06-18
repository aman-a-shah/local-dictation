/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The shared design system ships as TS/TSX source; transpile it here.
  transpilePackages: ["@local-dictation/ui"],
  poweredByHeader: false,
};

export default nextConfig;
