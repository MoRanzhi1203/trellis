import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'

const RATINGS: { key: 'again' | 'hard' | 'good' | 'easy'; label: string; className: string }[] = [
  { key: 'again', label: '忘记', className: 'danger' },
  { key: 'hard', label: '困难', className: '' },
  { key: 'good', label: '记得', className: 'primary' },
  { key: 'easy', label: '简单', className: '' },
]

export default function Study() {
  const due = useQuery({ queryKey: ['due'], queryFn: api.reviews.due })
  const [index, setIndex] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const client = useQueryClient()

  const cards = due.data ?? []
  const card = cards[Math.min(index, Math.max(cards.length - 1, 0))]

  const submit = useMutation({
    mutationFn: (result: string) =>
      api.reviews.submit({
        card_id: card.card_id,
        result,
        client_token: crypto.randomUUID(),
        duration_ms: 0,
      }),
    onSuccess: () => {
      setRevealed(false)
      setIndex((value) => value + 1)
      client.invalidateQueries({ queryKey: ['due'] })
      client.invalidateQueries({ queryKey: ['stats'] })
    },
  })

  const progress = useMemo(
    () => (cards.length === 0 ? 0 : Math.round((Math.min(index, cards.length) / cards.length) * 100)),
    [cards.length, index],
  )

  if (due.isLoading) return <div className="banner">加载中…</div>
  if (due.isError) return <div className="banner err">无法加载复习队列：{String(due.error)}</div>

  if (!card || index >= cards.length) {
    return (
      <div>
        <div className="page-head">
          <div>
            <h1>学习与复习</h1>
            <p>队列已清空</p>
          </div>
          <button onClick={() => { setIndex(0); setRevealed(false); due.refetch() }}>重新加载</button>
        </div>
        <div className="banner ok">今天没有到期的卡片，或者已经复习完了。</div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>学习与复习</h1>
          <p>到期卡片 {cards.length} 张 · FSRS 调度</p>
        </div>
        <span className="muted small">{progress}%</span>
      </div>

      <div className="card-study">
        <div className="small muted">{card.card_type} · {card.headword}</div>
        <div className="prompt">{card.prompt}</div>

        {revealed ? (
          <>
            <div className="answer">{card.answer || '（无答案）'}</div>
            <div className="rating-row">
              {RATINGS.map((rating) => (
                <button
                  key={rating.key}
                  className={rating.className}
                  disabled={submit.isPending}
                  onClick={() => submit.mutate(rating.key)}
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
        {submit.isError && <div className="banner err">{String(submit.error)}</div>}
      </div>
    </div>
  )
}
