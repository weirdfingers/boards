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
        protocol: "https",
        hostname: "zayxusljqgchxxjoxkuw.supabase.co",
      },
    ],
  },
};

module.exports = nextConfig;
