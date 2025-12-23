/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
  // Required for GitHub Pages subdirectory deployment
  basePath: '/pharma-rag',
  assetPrefix: '/pharma-rag/',
};

module.exports = nextConfig;
