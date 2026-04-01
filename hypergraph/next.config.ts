import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
    root: path.resolve(process.cwd(), ".."),
  },
  serverExternalPackages: ["@hyperbrowser/sdk"],
};

export default nextConfig;
