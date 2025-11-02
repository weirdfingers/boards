/**
 * Custom image loader for Next.js
 * Rewrites NEXT_PUBLIC_API_URL to INTERNAL_API_URL in the image URL query parameter
 * so that when Next.js's server-side image optimizer fetches the image,
 * it uses the internal Docker network URL instead of localhost
 */
export default function imageLoader({ src, width, quality }) {
  const publicApiUrl = process.env.NEXT_PUBLIC_API_URL;
  const internalApiUrl = process.env.INTERNAL_API_URL;

  // If we have an internal API URL and the src uses the public one, rewrite it
  let targetSrc = src;
  if (internalApiUrl && publicApiUrl && src.includes(publicApiUrl)) {
    targetSrc = src.replace(publicApiUrl, internalApiUrl);
  }

  return `/_next/image?url=${encodeURIComponent(targetSrc)}&w=${width}&q=${quality || 75}`;
}
