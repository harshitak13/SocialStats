import { useState } from 'react'
import axios from 'axios'

import ChatPanel from './components/ChatPanel.jsx'
import URLInput from './components/URLInput.jsx'
import VideoCard from './components/VideoCard.jsx'
import { API_URL, assertApiConfigured } from './lib/api.js'

function createSessionId() {
  if (window.crypto?.randomUUID) {
    return window.crypto.randomUUID()
  }
  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export default function App() {
  const [videoA, setVideoA] = useState(null)
  const [videoB, setVideoB] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [sessionId] = useState(createSessionId)
  const [ingested, setIngested] = useState(false)

  const handleIngest = async (youtubeUrl, instagramUrl) => {
    setIsLoading(true)
    setError(null)

    try {
      assertApiConfigured()
      const response = await axios.post(`${API_URL}/api/ingest`, {
        youtube_url: youtubeUrl,
        instagram_url: instagramUrl
      })
      setVideoA(response.data.video_a)
      setVideoB(response.data.video_b)
      setIngested(true)
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(detail || err.message || 'SocialStats could not analyze those videos. Check the URLs and try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-[#0f0f0f] text-[#f0f0f0]">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-4 py-5 sm:px-6 lg:px-8">
        <header className="mb-5 flex flex-col gap-1 border-b border-[#252525] pb-4">
          <h1 className="text-2xl font-bold tracking-normal text-white">SocialStats</h1>
          <p className="text-sm text-gray-400">AI-powered video analytics</p>
        </header>

        {!ingested ? (
          <section className="flex flex-1 items-center justify-center">
            <URLInput onIngest={handleIngest} isLoading={isLoading} error={error} />
          </section>
        ) : (
          <section className="grid flex-1 grid-rows-[auto_minmax(360px,1fr)] gap-5">
            <div className="grid gap-4 lg:grid-cols-2">
              <VideoCard metadata={videoA} label="Video A" />
              <VideoCard metadata={videoB} label="Video B" />
            </div>
            <ChatPanel sessionId={sessionId} />
          </section>
        )}
      </div>
    </main>
  )
}
