import type { NextConfig } from 'next'
import path from 'path'

const nextConfig: NextConfig = {
  output: 'standalone',
  turbopack: {
    root: path.resolve(__dirname),
  },
  async rewrites() {
    return [
      {
        source: '/backend/:path*',
        destination: 'http://api:8000/:path*',
      },
    ]
  },
}

export default nextConfig
