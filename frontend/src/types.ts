export interface Sense {
  id: number
  pos: string
  definition_zh: string
  definition_en: string
  order_no: number
  is_primary: boolean
  examples: { id: number; text: string; translation_zh: string }[]
  collocations: { id: number; pattern: string; note: string }[]
}

export interface Spelling {
  id: number
  spelling: string
  variant_type: string
  is_primary: boolean
}

export interface Pronunciation {
  id: number
  ipa: string
  accent: string
}

export interface Lexeme {
  id: number
  headword: string
  kind: string
  status: string
  created_at: string
  updated_at: string
  spellings: Spelling[]
  pronunciations: Pronunciation[]
  senses: Sense[]
  etymologies: { id: number; description_zh: string; confidence: string; status: string }[]
  trait: { id: number; main_level: string; memory_cost: string; rationale: string; advice: string } | null
}

export interface Page<T> {
  total: number
  offset: number
  limit: number
  items: T[]
}

export interface GraphNode {
  id: number
  node_type: string
  label: string
  lexeme_id: number | null
  morpheme_id: number | null
  unit_id: number | null
  meta: Record<string, unknown>
}

export interface GraphEdge {
  id: number
  source_node_id: number
  target_node_id: number
  relation_type: string
  status: string
  directed: boolean
  evidence: string
}

export interface GraphView {
  nodes: GraphNode[]
  edges: GraphEdge[]
  truncated: boolean
}

export interface DueCard {
  card_id: number
  lexeme_id: number
  headword: string
  card_type: string
  prompt: string
  answer: string
  due_at: string | null
  mode: string
  reps: number
  stability: number
  difficulty: number
}

export interface Stats {
  total_lexemes: number
  total_cards: number
  due_today: number
  learned_today: number
  reviewed_today: number
  accuracy_today: number
  streak_days: number
  weak_words: { headword: string; misses: number }[]
}

export interface Book {
  id: number
  title: string
  description: string
}

export interface Unit {
  id: number
  book_id: number
  title: string
  order_no: number
  kind: string
  note: string
  word_count: number
}
