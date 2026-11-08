import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import type { StudyCard } from '../types'

const RATINGS: { key: 'again' | 'hard' | 'good' | 'easy'; label: string }[] = [
  { key: 'again', label: '重来' },
  { key: 'hard', label: '困难' },
  { key: 'good', label: '良好' },
  { key: 'easy', label: '简单' },
]

type Result = { lexeme_id: number; headword: string; result: string }

export default function Test() {
  const [unitId, setUnitId] = useState<number | undefined>(undefined)
  const [order, setOrder] = useState<'sequential' | 'random'>('random')
  const [index, setIndex] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const [results, setResults] = useState<Result[]>([])

  const units = useQuery({
    queryKey: ['units-all'],
    queryFn: async () => {
      const books = await api.books.list()
      const nested = await Promise.all(books.map((book) => api.books.units(book.id)))
      return nested.flat().sort((a, b) => a.order_no - b.order_no)
    },
  })

  useEffect(() => {
    if (!unitId && units.data && units.data.length > 0) {
      setUnitId(units.data[0].id)
    }
  }, [unitId, units.data])

  const cards = useQuery({
    queryKey: ['study-cards', unitId],
    queryFn: () => api.study.cards(unitId as number),
    enabled: Boolean(unitId),
  })

  const items = useMemo(() => {
    const list: StudyCard[] = cards.data?.items ?? []
    if (order === 'sequential') return list
    const copy = [...list]
    for (let i = copy.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1))
      ;[copy[i], copy[j]] = [copy[j], copy[i]]
    }
    return copy
  }, [cards.data, order])

  const card = items[Math.min(index, Math.max(items.length - 1, 0))]
  const finished = items.length > 0 && index >= items.length
  const correct = results.filter((item) => item.result === 'good' || item.result === 'easy').length
  const accuracy = results.length === 0 ? 0 : Math.round((correct / results.length) * 100)

  const submit = useMutation({
    mutationFn: (result: string) =>
      api.reviews.submit({
        card_id: card?.card_id,
        result,
        client_token: crypto.randomUUID(),
        duration_ms: 0,
      }),
    onSuccess: (_data, result) => {
      if (card) {
        setResults((prev) => [
          ...prev,
          { lexeme_id: card.lexeme_id, headword: card.headword, result },
        ])
      }
      setRevealed(false)
      setIndex((value) => value + 1)
    },
  })

  const rate = (result: string) => {
    if (!card?.card_id || submit.isPending) return
    submit.mutate(result)
  }

  const reset = () => {
    setIndex(0)
    setRevealed(false)
    setResults([])
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>识别测试</h1>
          <p>只看英文，判断词性和中文意思；不计拼写，不做中译英。</p>
        </div>
        <div className="toolbar" style={{ marginBottom: 0 }}>
          <select
            value={unitId ?? ''}
            onChange={(event) => {
              setUnitId(Number(event.target.value) || undefined)
              reset()
            }}
          >
            {(units.data ?? []).map((unit) => (
              <option key={unit.id} value={unit.id}>
                {unit.title}（{unit.word_count}）
              </option>
            ))}
          </select>
          <select
            value={order}
            onChange={(event) => {
              setOrder(event.target.value as typeof order)
              reset()
            }}
          >
            <option value="random">随机</option>
            <option value="sequential">顺序</option>
          </select>
          <Link to="/">
            <button>退出</button>
          </Link>
        </div>
      </div>

      <div className="toolbar">
        <span className="small muted">
          已答 {results.length} / {items.length} · 正确 {correct} · 正确率 {accuracy}%
        </span>
      </div>

      {finished && (
        <div className="card-study">
          <div className="small muted">测试完成</div>
          <div className="prompt">
            {correct} / {results.length} 正确
          </div>
          <div className="answer" style={{ fontSize: 20 }}>
            正确率 {accuracy}%
          </div>
          <div className="toolbar">
            <button className="primary" onClick={reset}>
              再测一轮
            </button>
            <Link to="/">
              <button>返回首页</button>
            </Link>
          </div>
        </div>
      )}

      {!finished && card && (
        <div className="card-study">
          <div className="small muted">
            {index + 1} / {items.length}
          </div>
          <div className="prompt" style={{ fontSize: 42 }}>
            {card.headword}
          </div>
          {revealed ? (
            <>
              <div className="answer" style={{ whiteSpace: 'pre-line', fontSize: 17, lineHeight: 1.8 }}>
                {card.answer || '（暂无释义）'}
              </div>
              <div className="rating-row">
                {RATINGS.map((rating) => (
                  <button
                    key={rating.key}
                    className={rating.key === 'good' ? 'primary' : ''}
                    disabled={!card.card_id || submit.isPending}
                    onClick={() => rate(rating.key)}
                  >
                    {rating.label}
                  </button>
                ))}
              </div>
            </>
          ) : (
            <button className="primary" onClick={() => setRevealed(true)}>
              显示答案
            </button>
          )}
        </div>
      )}
    </div>
  )
}
