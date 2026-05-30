const badgeStyles = {
  'Video A': 'bg-blue-500/15 text-blue-300 border-blue-500/40',
  'Video B': 'bg-purple-500/15 text-purple-300 border-purple-500/40'
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString()
}

function engagementClass(value) {
  if (value > 5) {
    return 'text-green-400'
  }
  if (value >= 2) {
    return 'text-yellow-300'
  }
  return 'text-red-300'
}

export default function VideoCard({ metadata, label }) {
  if (!metadata) {
    return null
  }

  const hashtags = metadata.hashtags || []
  const engagementRate = Number(metadata.engagement_rate || 0)

  return (
    <article className="rounded-xl border border-[#2a2a2a] bg-[#151515] p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${badgeStyles[label]}`}>
          {label}
        </span>
        <span className="text-xs text-gray-500">{metadata.upload_date || 'No upload date'}</span>
      </div>

      <h2 className="line-clamp-2 min-h-[3.5rem] text-lg font-semibold leading-7 text-white">
        {metadata.title}
      </h2>

      <p className="mt-2 text-sm text-gray-400">
        {metadata.creator}
        {metadata.follower_count > 0 ? ` · ${formatNumber(metadata.follower_count)} followers` : ''}
      </p>

      <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
        <Stat label="Views" value={formatNumber(metadata.views)} />
        <Stat label="Likes" value={formatNumber(metadata.likes)} />
        <Stat label="Comments" value={formatNumber(metadata.comments)} />
        <Stat label="Duration" value={metadata.duration || '0:00'} />
      </div>

      <div className="mt-5 rounded-lg border border-[#262626] bg-[#101010] p-4">
        <p className="text-xs uppercase tracking-normal text-gray-500">Engagement Rate</p>
        <p className={`mt-1 text-3xl font-bold ${engagementClass(engagementRate)}`}>
          {engagementRate.toLocaleString()}%
        </p>
      </div>

      <div className="mt-4 flex gap-2 overflow-x-auto pb-1">
        {hashtags.slice(0, 5).map((tag) => (
          <span key={tag} className="shrink-0 rounded-full border border-[#333] bg-[#111] px-2.5 py-1 text-xs text-gray-300">
            {tag}
          </span>
        ))}
        {!hashtags.length ? <span className="text-xs text-gray-500">No hashtags found</span> : null}
      </div>
    </article>
  )
}

function Stat({ label, value }) {
  return (
    <div className="rounded-lg border border-[#262626] bg-[#101010] p-3">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 truncate font-semibold text-gray-100">{value}</p>
    </div>
  )
}
