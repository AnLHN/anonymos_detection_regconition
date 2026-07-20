const { PHASE_DEVELOPMENT_SERVER } = require('next/constants');

/** @type {import('next').NextConfig} */
module.exports = (phase) => {
  const isDev = phase === PHASE_DEVELOPMENT_SERVER;
  const distDir = process.env.NEXT_DIST_DIR;

  return {
    ...(distDir ? { distDir } : {}),
    ...(isDev ? {} : { output: 'standalone' }),
    allowedDevOrigins: [
      '192.168.2.182',
      'http://192.168.2.182:3000',
    ],
    async rewrites() {
      const backendOrigin = process.env.BACKEND_ORIGIN || `http://127.0.0.1:${process.env.BACKEND_PORT || '8000'}`;
      return [
        {
          source: '/api/:path*',
          destination: `${backendOrigin}/:path*`,
        },
      ];
    },
    async redirects() {
      return [
        {
          source: '/index.html',
          destination: '/',
          permanent: true,
        },
      ];
    },
  };
};
