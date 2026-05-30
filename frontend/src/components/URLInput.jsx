import { useState } from 'react'

import LoadingSpinner from './LoadingSpinner.jsx'

export default function URLInput({ onIngest, isLoading, error }) {
  const [youtubeUrl, setYoutubeUrl] = useState('')
  const [instagramUrl, setInstagramUrl] = useState('')

  const canSubmit = youtubeUrl.trim() && instagramUrl.trim() && !isLoading

  const handleSubmit = () => {
    if (!canSubmit) {
      return
    }
    onIngest(youtubeUrl.trim(), instagramUrl.trim())
  }

  return (
    <div className="w-full max-w-xl rounded-xl border border-[#2a2a2a] bg-[#1a1a1a] p-6 shadow-2xl shadow-black/30">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-white">Analyze Your Videos</h2>
        <p className="mt-1 text-sm text-gray-400">Paste one YouTube video and one public Instagram Reel.</p>
      </div>

      <div className="space-y-4">
        <input
          className="w-full rounded-lg border border-[#333] bg-[#101010] px-4 py-3 text-white outline-none transition focus:border-blue-500"
          placeholder="YouTube URL (Video A)"
          value={youtubeUrl}
          onChange={(event) => setYoutubeUrl(event.target.value)}
        />
        <input
          className="w-full rounded-lg border border-[#333] bg-[#101010] px-4 py-3 text-white outline-none transition focus:border-purple-500"
          placeholder="Instagram Reel URL (Video B)"
          value={instagramUrl}
          onChange={(event) => setInstagramUrl(event.target.value)}
        />

        <button
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-white px-4 py-3 font-semibold text-black transition hover:bg-gray-200 disabled:bg-gray-700 disabled:text-gray-400"
          disabled={!canSubmit}
          onClick={handleSubmit}
        >
          {isLoading ? <LoadingSpinner size="sm" /> : null}
          {isLoading ? 'Analyzing...' : 'Analyze with SocialStats'}
        </button>

        {error ? <p className="rounded-lg bg-red-950/60 px-3 py-2 text-sm text-red-300">{error}</p> : null}
      </div>
    </div>
  )
}
