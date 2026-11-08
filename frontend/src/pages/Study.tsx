import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../services/api'

const RATINGS: { key: 'again' | 'hard' | 'good' | 'easy'; label: string; hint: string }[] = [
  { key: 'again', label: '重来', hint: '完全不认识' },
  { key: 'hard', label: '困难', hint: '只记得一部分' },
  { key: 'good', label: '良好', hint: '主要词性和释义都对' },
  { key: 'easy', label: '简单', hint: '快速、完整' },
]

export default function Study() {
  const params = new URLSearchParams(window.location.search)
  const [unitId, setUnitId] = useState<number | undefined>(undefined)
  const [index, setIndex] = useState(0)
  const [revealed, setRevealed] = useState(params.get('reveal') === '1')
  const [done, setDone] = useState<Set<number>>(new Set())
  const client = useQueryClient()

  const units = useQuery({
    queryKey: ['units-all'],
    queryFn: async () => {
      const books = await api.books.list()
      const nested = await Promise.all(books.map((book) => api.books.units(book.id)))
      return nested.flat().sort((a, b) => a.order_no - b.order_no)
    },
  })

  const PROGRESS_KEY = 'trellis.study.progress.v1'

  useEffect(() => {
    if (unitId) return
    const raw = localStorage.getItem(PROGRESS_KEY)
    if (raw) {
      try {
        const saved = JSON.parse(raw) as { unitId?: number; index?: number }
        if (saved.unitId) {
          setUnitId(saved.unitId)
          if (typeof saved.index === 'number') setIndex(saved.index)
          return
        }
      } catch {
        // ignore corrupt progress
      }
    }
    if (units.data && units.data.length > 0) {
      setUnitId(units.data[0].id)
    }
  }, [unitId, units.data])

  useEffect(() => {
    if (!unitId) return
    localStorage.setItem(PROGRESS_KEY, JSON.stringify({ unitId, index }))
  }, [unitId, index])

  const cards = useQuery({
    queryKey: ['study-cards', unitId],
    queryFn: () => api.study.cards(unitId as number),
    enabled: Boolean(unitId),
  })

  const items = useMemo(() => cards.data?.items ?? [], [cards.data])
  const card = items[Math.min(index, Math.max(items.length - 1, 0))]
  const finished = items.length > 0 && index >= items.length

  const submit = useMutation({
    mutationFn: (result: string) =>
      api.reviews.submit({
        card_id: card?.card_id,
        result,
        client_token: crypto.randomUUID(),
        duration_ms: 0,
      }),
    onSuccess: () => {
      if (card) setDone((prev) => new Set(prev).add(card.lexeme_id))
      setRevealed(false)
      setIndex((value) => value + 1)
      client.invalidateQueries({ queryKey: ['stats'] })
    },
  })

  const canRate = Boolean(card?.card_id) && !submit.isPending

  const rate = (result: string) => {
    if (!canRate) return
    submit.mutate(result)
  }

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const tag = (event.target as HTMLElement)?.tagName
      if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') return
      if (event.key === ' ' || event.key === 'Enter') {
        event.preventDefault()
        if (!revealed) setRevealed(true)
        return
      }
      if (revealed && ['1', '2', '3', '4'].includes(event.key)) {
        event.preventDefault()
        rate(RATINGS[Number(event.key) - 1].key)
      }
      if (event.key === 'ArrowRight' && index < items.length) {
        setRevealed(false)
        setIndex((value) => Math.min(value + 1, items.length))
      }
      if (event.key === 'ArrowLeft' && index > 0) {
        setRevealed(false)
        setIndex((value) => value - 1)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  })

  const progress = items.length === 0 ? 0 : Math.round((Math.min(index, items.length) / items.length) * 100)
  const remaining = Math.max(items.length - index, 0)

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>识别学习</h1>
          <p>看英文，回忆词性和中文意思；不要求拼写，也不做中译英。</p>
        </div>
        <div className="toolbar" style={{ marginBottom: 0 }}>
          <select
            value={unitId ?? ''}
            onChange={(event) => {
              setUnitId(Number(event.target.value) || undefined)
              setIndex(0)
              setRevealed(false)
              setDone(new Set())
            }}
          >
            {(units.data ?? []).map((unit) => (
              <option key={unit.id} value={unit.id}>
                {unit.title}（{unit.word_count}）
              </option>
            ))}
          </select>
          <Link to="/">
            <button>退出</button>
          </Link>
        </div>
      </div>

      <div className="toolbar">
        <span className="small muted">
          进度 {Math.min(index, items.length)} / {items.length} · 剩余 {remaining} · 已完成 {done.size}
        </span>
        <div className="track" style={{ flex: 1, minWidth: 160 }}>
          <i style={{ width: `${progress}%` }} />
        </div>
      </div>

      {cards.isLoading && <div className="banner">加载中…</div>}
      {cards.isError && <div className="banner err">无法加载学习卡片：{String(cards.error)}</div>}

      {!cards.isLoading && !cards.isError && items.length === 0 && (
        <div className="banner">这个单元还没有词条。</div>
      )}

      {finished && (
        <div className="card-study">
          <div className="small muted">本轮完成</div>
          <div className="prompt">已完成 {items.length} 个单词</div>
          <div className="rating-row">
            <button
              className="primary"
              onClick={() => {
                setIndex(0)
                setRevealed(false)
                setDone(new Set())
              }}
            >
              再来一轮
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
            {card.order_no} / {items.length} · 第 {index + 1} 个
          </div>
          <div className="prompt" style={{ fontSize: 42, letterSpacing: 0.5 }}>
            {card.headword}
          </div>

          {revealed ? (
            <>
              <div
                className="answer"
                style={{ whiteSpace: 'pre-line', fontSize: 17, lineHeight: 1.8 }}
              >
                {card.answer || '（暂无释义）'}
              </div>
              <div className="rating-row">
                {RATINGS.map((rating) => (
                  <button
                    key={rating.key}
                    className={rating.key === 'good' ? 'primary' : ''}
                    title={rating.hint}
                    disabled={!canRate}
                    onClick={() => rate(rating.key)}
                  >
                    {rating.label}
                  </button>
                ))}
              </div>
              {submit.isError && <div className="banner err">{String(submit.error)}</div>}
            </>
          ) : (
            <button className="primary" onClick={() => setRevealed(true)}>
              显示答案（Space）
            </button>
          )}

          <div className="toolbar" style={{ marginTop: 16 }}>
            <button
              className="ghost"
              disabled={index === 0}
              onClick={() => {
                setRevealed(false)
                setIndex((value) => Math.max(0, value - 1))
              }}
            >
              ← 上一词
            </button>
            <span className="small muted">快捷键：Space 显示答案，1–4 评价，←/→ 切换</span>
          </div>
        </div>
      )}
    </div>
  )
}
