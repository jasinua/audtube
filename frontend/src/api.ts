// API base: same-origin in production; override with VITE_API_URL in dev.
export const API_BASE = import.meta.env.VITE_API_URL ?? '';

// Shared secret sent with API calls (set VITE_API_KEY in Netlify env).
const API_KEY = import.meta.env.VITE_API_KEY ?? '';

const authHeaders: Record<string, string> = API_KEY ? { 'X-API-Key': API_KEY } : {};

export interface VideoInfo {
  title: string;
  thumbnail: string | null;
  duration: number;
  channel: string | null;
}

export interface ConvertResult {
  job_id: string;
  filename: string;
  title: string;
  download_url: string;
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    return data.error ?? 'Something went wrong.';
  } catch {
    return 'Something went wrong.';
  }
}

export async function fetchInfo(url: string): Promise<VideoInfo> {
  const res = await fetch(`${API_BASE}/api/info?url=${encodeURIComponent(url)}`, {
    headers: authHeaders,
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function convert(
  url: string,
  format: 'mp3' | 'mp4',
  quality: string,
): Promise<ConvertResult> {
  const res = await fetch(`${API_BASE}/api/convert`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders },
    body: JSON.stringify({ url, format, quality }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export function downloadUrl(result: ConvertResult): string {
  return `${API_BASE}${result.download_url}?name=${encodeURIComponent(result.filename)}`;
}
