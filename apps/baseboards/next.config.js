/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  transpilePackages: ["@weirdfingers/boards"],
  images: {
    // Disable server-side optimization when running in a container
    // (the Next.js server can't reach localhost:8088 from inside Docker)
    unoptimized: process.env.NEXT_PUBLIC_CONTAINERIZED === "true",
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
