const configuredApiUrl = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || ''

export const API_URL = configuredApiUrl.replace(/\/+$/, '')

export function assertApiConfigured() {
  if (!API_URL && import.meta.env.PROD) {
    throw new Error('Missing VITE_API_URL. Add your deployed backend URL in the frontend deployment settings.')
  }
}
