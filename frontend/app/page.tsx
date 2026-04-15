"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

type Mode = "ad";

type GenerateResponse = {
  video_url: string;
  script: string;
  caption: string;
};

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const mode: Mode = "ad";
  const [tone, setTone] = useState("");
  const [logo, setLogo] = useState<File | null>(null);
  const [logoPreview, setLogoPreview] = useState("");
  const [copyStatus, setCopyStatus] = useState<"" | "script" | "caption">("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<GenerateResponse | null>(null);

  const backendUrl = useMemo(
    () => process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000",
    []
  );

  const videoSource = result ? `${backendUrl}${result.video_url}` : "";

  function setLogoFile(file: File | null) {
    if (logoPreview) {
      URL.revokeObjectURL(logoPreview);
    }
    setLogo(file);
    if (!file) {
      setLogoPreview("");
      return;
    }
    setLogoPreview(URL.createObjectURL(file));
  }

  useEffect(() => {
    return () => {
      if (logoPreview) {
        URL.revokeObjectURL(logoPreview);
      }
    };
  }, [logoPreview]);

  async function handleGenerate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setCopyStatus("");

    if (!prompt.trim()) {
      setError("Please enter a prompt before generating.");
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("prompt", prompt);
      formData.append("mode", mode);
      formData.append("audience", "");
      formData.append("tone", tone);
      if (logo) {
        formData.append("logo", logo);
      }

      const response = await fetch(`${backendUrl}/generate`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail || "Failed to generate video.");
      }

      const payload = (await response.json()) as GenerateResponse;
      setResult(payload);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unexpected error";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  function handleRegenerate() {
    setResult(null);
    setError("");
    setCopyStatus("");
  }

  async function handleCopy(content: string, target: "script" | "caption") {
    try {
      await navigator.clipboard.writeText(content);
      setCopyStatus(target);
      setTimeout(() => setCopyStatus(""), 1200);
    } catch {
      setError("Unable to copy content right now.");
    }
  }

  return (
    <main className="creation-surface relative min-h-screen overflow-x-hidden px-4 py-10 md:px-8">
      <div className="noise-overlay pointer-events-none absolute inset-0" />
      <div className="blob blob-left pointer-events-none absolute" />
      <div className="blob blob-right pointer-events-none absolute" />
      <div className="blob blob-mid pointer-events-none absolute" />
      <div className="blob blob-bottom pointer-events-none absolute" />
      <div className="grid-fade pointer-events-none absolute inset-0" />

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55 }}
        className="mx-auto relative z-10 flex w-full max-w-6xl flex-col gap-8"
      >
        <section className="space-y-3 px-2 text-center md:px-6">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-500">AI Video Creator</p>
          <h1 className="mx-auto max-w-5xl bg-gradient-to-r from-blue-700 via-indigo-600 to-violet-600 bg-clip-text text-3xl font-extrabold leading-[1.1] tracking-tight text-transparent sm:text-5xl lg:text-6xl">
            Create videos that drive real business
          </h1>
        </section>

        <section className="mx-auto w-full max-w-5xl">
          <form className="space-y-4" onSubmit={handleGenerate}>
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-medium text-slate-700">Goal</p>
              <span className="rounded-full bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white shadow-md">
                Business Content
              </span>

              <select
                value={tone}
                onChange={(e) => setTone(e.target.value)}
                className="ml-auto rounded-full border border-white/70 bg-white/80 px-4 py-1.5 text-sm text-slate-700 outline-none ring-2 ring-transparent transition focus:border-indigo-300 focus:ring-indigo-400/25"
              >
                <option value="">Tone (optional)</option>
                <option value="Confident">Confident</option>
                <option value="Playful">Playful</option>
                <option value="Professional">Professional</option>
                <option value="Inspirational">Inspirational</option>
              </select>
            </div>

            <div className="input-shell flex items-center gap-3 rounded-[2rem] bg-white/85 p-3 shadow-lg transition-all focus-within:shadow-[0_0_0_6px_rgba(129,140,248,0.16)]">
              <button
                type="button"
                onClick={() => document.getElementById("logo-upload")?.click()}
                className="rounded-full bg-indigo-50 px-3 py-2 text-xs font-medium text-indigo-700 transition hover:bg-indigo-100"
              >
                + Logo
              </button>

              <input
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="w-full border-none bg-transparent px-1 py-2 text-sm text-slate-800 outline-none placeholder:text-slate-400 md:text-base"
                placeholder="What do you want your audience to understand or act on?"
                required
              />

              <motion.button
                whileHover={{ scale: loading ? 1 : 1.04 }}
                whileTap={{ scale: loading ? 1 : 0.98 }}
                disabled={loading}
                type="submit"
                className="rounded-full bg-gradient-to-r from-indigo-600 to-purple-600 px-5 py-2.5 text-sm font-semibold text-white shadow-[0_0_16px_rgba(99,102,241,0.35)] transition hover:from-indigo-500 hover:to-purple-500 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {loading ? "Creating your video…" : "Generate Video ✨"}
              </motion.button>

              <input
                id="logo-upload"
                type="file"
                accept="image/*"
                onChange={(e) => setLogoFile(e.target.files?.[0] || null)}
                className="hidden"
              />
            </div>

            {logoPreview && (
              <div className="flex items-center gap-2 text-sm text-slate-600">
                <img
                  src={logoPreview}
                  alt="Logo preview"
                  className="h-8 w-8 rounded-md border border-slate-200 bg-white object-contain p-0.5"
                />
                <span>Add your logo for branding</span>
              </div>
            )}

            {error && <p className="text-sm text-red-600">{error}</p>}
          </form>
        </section>

        <section className="space-y-4">
          <div className="preview-shell relative w-full overflow-hidden rounded-2xl p-[2px] shadow-xl">
            <div className="preview-shimmer pointer-events-none absolute inset-0" />

            <AnimatePresence mode="wait">
              {result ? (
                <motion.div
                  key="video-preview"
                  initial={{ opacity: 0, scale: 0.985 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.35 }}
                  className="relative z-10"
                >
                  <video
                    controls
                    src={videoSource}
                    className="aspect-video w-full rounded-2xl bg-slate-200"
                  />
                </motion.div>
              ) : (
                <motion.div
                  key="video-placeholder"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="relative z-10 flex aspect-video items-center justify-center rounded-2xl bg-white/80"
                >
                  <p className="text-sm font-medium text-slate-600 md:text-base">Your AI video will appear here</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <div className="flex items-center gap-3">
            <a
              href={videoSource || "#"}
              download
              className={`rounded-full px-5 py-2 text-sm font-semibold text-white transition ${
                result ? "bg-indigo-600 hover:bg-indigo-500" : "pointer-events-none bg-slate-300"
              }`}
            >
              Download Video
            </a>
            <button
              onClick={handleRegenerate}
              type="button"
              className="rounded-full border border-slate-300 bg-white/85 px-5 py-2 text-sm font-medium text-slate-700"
            >
              Reset
            </button>
          </div>

          {result && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="grid gap-4 md:grid-cols-2"
            >
              <div className="rounded-2xl bg-white/70 p-4 shadow-sm">
                <div className="mb-2 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-700">Script</h3>
                  <button
                    onClick={() => handleCopy(result.script, "script")}
                    type="button"
                    className="rounded-full border border-slate-300 bg-white px-3 py-1 text-xs font-medium text-slate-700"
                  >
                    {copyStatus === "script" ? "Copied" : "Copy"}
                  </button>
                </div>
                <p className="whitespace-pre-wrap text-sm text-slate-700">{result.script}</p>
              </div>

              <div className="rounded-2xl bg-white/70 p-4 shadow-sm">
                <div className="mb-2 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-700">Caption</h3>
                  <button
                    onClick={() => handleCopy(result.caption, "caption")}
                    type="button"
                    className="rounded-full border border-slate-300 bg-white px-3 py-1 text-xs font-medium text-slate-700"
                  >
                    {copyStatus === "caption" ? "Copied" : "Copy"}
                  </button>
                </div>
                <p className="whitespace-pre-wrap text-sm text-slate-700">{result.caption}</p>
              </div>
            </motion.div>
          )}
        </section>
      </motion.div>
    </main>
  );
}
