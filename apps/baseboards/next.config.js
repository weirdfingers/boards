/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@weirdfingers/boards"],
  images: {
    // Use custom loader when INTERNAL_API_URL is set (Docker environment)
    // This allows server-side image optimization to fetch from internal network
    ...(process.env.INTERNAL_API_URL && {
      loader: "custom",
      loaderFile: "./imageLoader.js",
    }),
    remotePatterns: [
      {
        protocol: "http",
        hostname: "localhost",
        port: "8088",
        pathname: "/api/storage/**",
      },
      // Allow internal Docker hostname for image optimization
      ...(process.env.INTERNAL_API_URL
        ? [
            {
              protocol: "http",
              hostname: "api",
              port: "8800",
              pathname: "/api/storage/**",
            },
          ]
        : []),
    ],
  },
};

module.exports = nextConfig;
