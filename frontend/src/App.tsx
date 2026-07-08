import { useCallback, useEffect, useRef, useState } from 'react';
import {
  convert,
  downloadUrl,
  fetchInfo,
  type ConvertResult,
  type VideoInfo,
} from './api';

type Format = 'mp3' | 'mp4';

const QUALITY: Record<Format, { value: string; label: string }[]> = {
  mp3: [
    { value: '128', label: '128 kbps' },
    { value: '192', label: '192 kbps' },
    { value: '320', label: '320 kbps' },
  ],
  mp4: [
    { value: '360', label: '360p' },
    { value: '720', label: '720p' },
    { value: '1080', label: '1080p' },
  ],
};

function formatDuration(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, '0')}`;
}

export default function App() {
  const [url, setUrl] = useState('');
  const [format, setFormat] = useState<Format>('mp3');
  const [quality, setQuality] = useState('192');
  const [info, setInfo] = useState<VideoInfo | null>(null);
  const [loadingInfo, setLoadingInfo] = useState(false);
  const [converting, setConverting] = useState(false);
  const [result, setResult] = useState<ConvertResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const debounceRef = useRef<number | undefined>(undefined);

  // Fetch metadata as soon as a plausible YouTube URL is present.
  useEffect(() => {
    window.clearTimeout(debounceRef.current);
    setResult(null);
    const trimmed = url.trim();
    if (!/youtube\.com|youtu\.be/.test(trimmed)) {
      setInfo(null);
      setError(null);
      return;
    }
    debounceRef.current = window.setTimeout(async () => {
      setLoadingInfo(true);
      setError(null);
      try {
        setInfo(await fetchInfo(trimmed));
      } catch (e) {
        setInfo(null);
        setError((e as Error).message);
      } finally {
        setLoadingInfo(false);
      }
    }, 500);
    return () => window.clearTimeout(debounceRef.current);
  }, [url]);

  // Keep quality valid when switching format (default to the mid option).
  useEffect(() => {
    setQuality(QUALITY[format][1].value);
  }, [format]);

  const handleConvert = useCallback(async () => {
    setConverting(true);
    setError(null);
    setResult(null);
    try {
      setResult(await convert(url.trim(), format, quality));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setConverting(false);
    }
  }, [url, format, quality]);

  const canConvert = !!info && !converting && !loadingInfo;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 text-slate-900 flex flex-col items-center px-4 py-10 sm:py-16 font-sans">
      <div className="w-full max-w-xl">
        <header className="text-center mb-8">
          <div className="text-4xl mb-2">🎵</div>
          <h1 className="text-3xl font-bold tracking-tight">audtube</h1>
          <p className="text-slate-500 mt-1">
            Paste a YouTube link to grab the audio or video.
          </p>
        </header>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5 sm:p-6">
          {/* URL input + convert */}
          <div className="flex flex-col sm:flex-row gap-2">
            <input
              type="url"
              inputMode="url"
              autoCapitalize="off"
              autoCorrect="off"
              spellCheck={false}
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://youtube.com/watch?v=..."
              className="flex-1 rounded-xl border border-slate-300 px-4 py-3 text-base outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
            <button
              onClick={handleConvert}
              disabled={!canConvert}
              className="rounded-xl bg-indigo-600 text-white font-semibold px-6 py-3 hover:bg-indigo-700 active:scale-[0.98] transition disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {converting ? 'Converting…' : 'Convert'}
            </button>
          </div>

          {/* Format + quality */}
          <div className="flex items-center gap-3 mt-4">
            <div className="inline-flex rounded-lg bg-slate-100 p-1">
              {(['mp3', 'mp4'] as Format[]).map((f) => (
                <button
                  key={f}
                  onClick={() => setFormat(f)}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition ${
                    format === f
                      ? 'bg-white shadow-sm text-slate-900'
                      : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  {f.toUpperCase()}
                </button>
              ))}
            </div>
            <select
              value={quality}
              onChange={(e) => setQuality(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm bg-white outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {QUALITY[format].map((q) => (
                <option key={q.value} value={q.value}>
                  {q.label}
                </option>
              ))}
            </select>
          </div>

          {/* Loading metadata */}
          {loadingInfo && (
            <p className="mt-5 text-sm text-slate-500 animate-pulse">Fetching video info…</p>
          )}

          {/* Error */}
          {error && (
            <div className="mt-5 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Result card */}
          {info && !error && (
            <div className="mt-5 rounded-xl border border-slate-200 overflow-hidden flex flex-col sm:flex-row">
              {info.thumbnail && (
                <img
                  src={info.thumbnail}
                  alt=""
                  className="w-full sm:w-40 h-40 sm:h-auto object-cover"
                />
              )}
              <div className="p-4 flex-1 flex flex-col">
                <h2 className="font-semibold leading-snug line-clamp-2">{info.title}</h2>
                <p className="text-sm text-slate-500 mt-1">
                  {info.channel ? `${info.channel} · ` : ''}
                  {formatDuration(info.duration)} ·{' '}
                  {format.toUpperCase()} {QUALITY[format].find((q) => q.value === quality)?.label}
                </p>

                <div className="mt-auto pt-3">
                  {converting && (
                    <div className="w-full">
                      <div className="h-2 rounded-full bg-slate-200 overflow-hidden">
                        <div className="h-full bg-indigo-600 animate-pulse w-2/3" />
                      </div>
                      <p className="text-xs text-slate-500 mt-1.5">
                        Downloading & converting…
                      </p>
                    </div>
                  )}
                  {result && !converting && (
                    <a
                      href={downloadUrl(result)}
                      className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 text-white font-semibold px-5 py-2.5 hover:bg-emerald-700 transition w-full sm:w-auto"
                    >
                      ⬇ Download {format.toUpperCase()}
                    </a>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        <footer className="text-center text-xs text-slate-400 mt-8">
          For personal use with content you own or that is licensed for reuse.
        </footer>
      </div>
    </div>
  );
}
