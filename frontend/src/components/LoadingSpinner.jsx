const sizes = {
  sm: 'h-4 w-4',
  md: 'h-6 w-6',
  lg: 'h-8 w-8'
}

export default function LoadingSpinner({ size = 'md' }) {
  return (
    <span
      className={`${sizes[size] || sizes.md} inline-block animate-spin rounded-full border-2 border-current border-t-transparent`}
      aria-label="Loading"
    />
  )
}
