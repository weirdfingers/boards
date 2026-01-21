/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  transpilePackages: ["@weirdfingers/boards"],
};

module.exports = nextConfig;
