/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: [
    "@weirdfingers/boards",
    "@weirdfingers/boards-auth-supabase",
  ],
  images: {
    remotePatterns: [
      {
        protocol: "http",
        hostname: "localhost",
        port: "8088",
        pathname: "/api/storage/**",
      },
    ],
  },
};

module.exports = nextConfig;
