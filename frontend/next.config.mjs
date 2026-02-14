/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "server.arcgisonline.com" },
      { protocol: "https", hostname: "earthengine.googleapis.com" },
      { protocol: "https", hostname: "api.mapbox.com" },
    ],
  },
};

export default nextConfig;
