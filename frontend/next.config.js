/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable React strict mode — catches potential bugs earlier
  reactStrictMode: true,

  // Environment variables prefixed with NEXT_PUBLIC_ are exposed to the browser
  // Other env vars (no prefix) are server-side only
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL,
  },
};

module.exports = nextConfig;
