import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // `standalone` tells Next.js to emit `.next/standalone/` containing a
  // minimal Node server plus only the modules the app actually imports.
  // Our runtime image copies that tree instead of the whole node_modules
  // folder, cutting the container size by roughly an order of magnitude
  // (important for Cloud Run cold-start latency).
  output: 'standalone',
};

export default nextConfig;
