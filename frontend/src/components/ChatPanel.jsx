import { useEffect, useRef, useState } from 'react'

import LoadingSpinner from './LoadingSpinner.jsx'
import MessageBubble from './MessageBubble.jsx'

const API_URL = import.meta.env.VITE_API_URL || ''

const suggestedQuestions = [
  'Why did Video A get more engagement than Video B?',
  "What's the engagement rate of each video?",
  'Compare the hooks in the first 5 seconds',
  "Who's the creator of Video B?",
  'Suggest improvements for Video B based on Video A'
]

export default function ChatPanel({ sessionId }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const scrollRef = useRef(null)

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const appendAssistantToken = (token) => {
    setMessages((current) => {
      const next = [...current]
      const last = next[next.length - 1]
      if (last?.role === 'assistant') {
        next[next.length - 1] = { ...last, content: `${last.content}${token}` }
      } else {
        next.push({ role: 'assistant', content: token, sources: [] })
      }
      return next
    })
  }

  const handleSend = async () => {
    const question = input.trim()
    if (!question || isStreaming) {
      return
    }

    setInput('')
    setMessages((current) => [...current, { role: 'user', content: question, sources: [] }])
    setIsStreaming(true)

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, session_id: sessionId })
      })

      if (!response.ok || !response.body) {
        throw new Error('SocialStats chat stream could not start.')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let complete = false

      while (!complete) {
        const { done, value } = await reader.read()
        if (done) {
          break
        }

        buffer += decoder.decode(value, { stream: true })
        const events = buffer.split('\n\n')
        buffer = events.pop() || ''

        for (const event of events) {
          if (!event.startsWith('data: ')) {
            continue
          }

          const piece = event.slice(6)
          if (piece === '[DONE]') {
            complete = true
            break
          }
          if (piece.startsWith('[ERROR]')) {
            appendAssistantToken(`\n${piece}`)
            complete = true
            break
          }
          appendAssistantToken(piece)
        }
      }
    } catch (err) {
      appendAssistantToken(`SocialStats chat failed: ${err.message}`)
    } finally {
      setIsStreaming(false)
    }
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Enter') {
      handleSend()
    }
  }

  return (
    <section className="flex min-h-0 flex-col rounded-xl border border-[#252525] bg-[#111]">
      <div className="border-b border-[#252525] px-4 py-3">
        <h2 className="font-semibold text-white">Chat with SocialStats AI</h2>
      </div>

      <div className="chat-scroll min-h-0 flex-1 overflow-y-auto px-4 py-4">
        {!messages.length ? (
          <div className="flex flex-wrap gap-2">
            {suggestedQuestions.map((question) => (
              <button
                key={question}
                className="rounded-full border border-[#333] bg-[#181818] px-3 py-2 text-left text-sm text-gray-300 hover:border-gray-500 hover:text-white"
                onClick={() => setInput(question)}
              >
                {question}
              </button>
            ))}
          </div>
        ) : null}

        <div className="mt-3 space-y-3">
          {messages.map((message, index) => (
            <MessageBubble
              key={`${message.role}-${index}`}
              role={message.role}
              content={message.content}
              sources={message.sources}
            />
          ))}
          <div ref={scrollRef} />
        </div>
      </div>

      <div className="border-t border-[#252525] p-4">
        {isStreaming ? (
          <p className="mb-2 flex items-center gap-2 text-sm text-gray-400">
            <LoadingSpinner size="sm" />
            SocialStats AI is thinking...
          </p>
        ) : null}
        <div className="flex gap-2">
          <input
            className="min-w-0 flex-1 rounded-lg border border-[#333] bg-[#0f0f0f] px-3 py-2 text-white outline-none focus:border-blue-500"
            placeholder="Ask about engagement, hooks, metadata, or transcript differences..."
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-400"
            disabled={isStreaming || !input.trim()}
            onClick={handleSend}
          >
            Send
          </button>
        </div>
      </div>
    </section>
  )
}
