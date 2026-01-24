/** @type {import('next').NextConfig} */
const nextConfig = {
  // 允许调用本地API
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ]
  },
}

module.exports = nextConfig
