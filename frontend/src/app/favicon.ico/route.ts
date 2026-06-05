export function GET() {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
    <rect width="64" height="64" rx="14" fill="#121d2b"/>
    <path d="M16 34c4-9 10-14 16-14s12 5 16 14c-4 7-10 11-16 11s-12-4-16-11Z" fill="#087e8b"/>
    <circle cx="32" cy="33" r="8" fill="#f8faf6"/>
    <circle cx="32" cy="33" r="4" fill="#d99a1e"/>
  </svg>`;

  return new Response(svg, {
    headers: {
      'content-type': 'image/svg+xml',
      'cache-control': 'public, max-age=31536000, immutable',
    },
  });
}
