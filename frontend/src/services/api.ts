import type {
  Book,
  DueCard,
  GraphView,
  Lexeme,
  Page,
  Stats,
  StudyCard,
  Unit,
} from '../types'

const BASE = '/api'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers ?? {}) },
    ...options,
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`${response.status}: ${detail}`)
  }
  return response.json() as Promise<T>
}

export const api = {
  health: () => request<{ status: string }>('/health'),
  words: {
    list: (params: Record<string, string | number | undefined>) => {
      const query = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== '') query.set(key, String(value))
      })
      return request<Page<Lexeme>>(`/words?${query.toString()}`)
    },
    get: (id: number) => request<Lexeme>(`/words/${id}`),
    create: (payload: unknown) =>
      request<Lexeme>('/words', { method: 'POST', body: JSON.stringify(payload) }),
    update: (id: number, payload: unknown) =>
      request<Lexeme>(`/words/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
    remove: (id: number) => request<{ ok: boolean }>(`/words/${id}`, { method: 'DELETE' }),
    search: (q: string) => request<Lexeme[]>(`/words/search?q=${encodeURIComponent(q)}`),
  },
  graph: {
    view: (params: Record<string, string | number | undefined>) => {
      const query = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== '') query.set(key, String(value))
      })
      return request<GraphView>(`/graph?${query.toString()}`)
    },
    neighbors: (nodeId: number, depth = 1) =>
      request<GraphView>(`/graph/nodes/${nodeId}/neighbors?depth=${depth}`),
    createEdge: (payload: unknown) =>
      request<unknown>('/graph/edges', { method: 'POST', body: JSON.stringify(payload) }),
    removeEdge: (id: number) => request<{ ok: boolean }>(`/graph/edges/${id}`, { method: 'DELETE' }),
  },
  books: {
    list: () => request<Book[]>('/books'),
    units: (bookId: number) => request<Unit[]>(`/books/${bookId}/units`),
  },
  reviews: {
    due: () => request<DueCard[]>('/reviews/due'),
    submit: (payload: unknown) => request<unknown>('/reviews/submit', { method: 'POST', body: JSON.stringify(payload) }),
    history: () => request<unknown[]>('/reviews/history'),
  },
  study: {
    cards: (unitId: number) =>
      request<{ unit: string; items: StudyCard[] }>(`/study/cards?unit_id=${unitId}`),
  },
  stats: () => request<Stats>('/statistics/overview'),
  imports: {
    legacy: () => request<{ counts: Record<string, number>; errors: string[]; notes: string[] }>('/imports/legacy', { method: 'POST' }),
    backup: () => request<{ file: string; size: number }>('/backup', { method: 'POST' }),
    restore: (file: string) =>
      request<{ ok: boolean }>('/restore', { method: 'POST', body: JSON.stringify({ file }) }),
  },
}
