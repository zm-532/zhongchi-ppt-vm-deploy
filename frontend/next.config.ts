import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",

  async rewrites() {
    // 后端地址，默认 127.0.0.1:8010
    // 可通过环境变量 BACKEND_URL 覆盖（例如 Docker 中设为 http://backend:8010）
    const backendUrl = process.env.BACKEND_URL || "http://127.0.0.1:8010";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
