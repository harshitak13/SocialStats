function parseContent(content, explicitSources) {
  const sources = [...(explicitSources || [])]
  const sourceMatch = content.match(/Sources:\s*((?:\[Video [^\]]+\]\s*)+)/)
  let displayContent = content

  if (sourceMatch) {
    displayContent = content.replace(sourceMatch[0], '').trim()
    const parsedSources = sourceMatch[1].match(/\[Video [^\]]+\]/g) || []
    parsedSources.forEach((source) => sources.push(source))
  }

  return { displayContent, sources }
}

export default function MessageBubble({ role, content, sources }) {
  const { displayContent, sources: renderedSources } = parseContent(content, sources)
  const isUser = role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] whitespace-pre-wrap rounded-xl px-4 py-3 text-sm leading-6 ${
          isUser
            ? 'bg-[#1d4ed8] text-white'
            : 'border border-[#2a2a2a] bg-[#1e1e1e] text-gray-100'
        }`}
      >
        <p>{displayContent}</p>
        {!isUser && renderedSources.length ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {renderedSources.map((source, index) => (
              <span key={`${source}-${index}`} className="rounded-full border border-[#3a3a3a] px-2 py-1 text-xs text-gray-400">
                {typeof source === 'string'
                  ? source
                  : `[Video ${source.video_id}, Chunk ${source.chunk_index}]`}
              </span>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  )
}
