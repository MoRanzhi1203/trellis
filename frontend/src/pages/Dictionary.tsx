import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import type { Lexeme } from '../types'

const PAGE_SIZE = 20

export default function Dictionary() {
  const [query, setQuery] = useState('')
  const [offset, setOffset] = useState(0)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [headword, setHeadword] = useState('')
  const [pos, setPos] = useState('n.')
  const [definition, setDefinition] = useState('')
  const client = useQueryClient()

  const words = useQuery({
    queryKey: ['words', query, offset],
    queryFn: () => api.words.list({ q: query, offset, limit: PAGE_SIZE }),
  })
  const detail = useQuery({
    queryKey: ['word', selectedId],
    queryFn: () => api.words.get(selectedId as number),
    enabled: selectedId !== null,
  })

  const create = useMutation({
    mutationFn: () =>
      api.words.create({
        headword,
        kind: 'word',
        senses: [{ pos, definition_zh: definition }],
      }),
    onSuccess: (lexeme) => {
      setShowCreate(false)
      setHeadword('')
      setDefinition('')
      setSelectedId(lexeme.id)
      client.invalidateQueries({ queryKey: ['words'] })
      client.invalidateQueries({ queryKey: ['stats'] })
    },
  })

  const remove = useMutation({
    mutationFn: (id: number) => api.words.remove(id),
    onSuccess: () => {
      setSelectedId(null)
      client.invalidateQueries({ queryKey: ['words'] })
      client.invalidateQueries({ queryKey: ['graph'] })
      client.invalidateQueries({ queryKey: ['stats'] })
    },
  })

  const total = words.data?.total ?? 0
  const pages = useMemo(() => Math.ceil(total / PAGE_SIZE), [total])
  const items = words.data?.items ?? []

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>词库</h1>
          <p>共 {total} 条匹配词目 · 点击查看详情与图谱关联</p>
        </div>
        <button className="primary" onClick={() => setShowCreate((value) => !value)}>
          {showCreate ? '收起' : '新增词条'}
        </button>
      </div>

      {showCreate && (
        <div className="panel">
          <h2>新增词条</h2>
          <div className="toolbar">
            <input placeholder="headword" value={headword} onChange={(event) => setHeadword(event.target.value)} />
            <input placeholder="词性，如 n. / v." value={pos} onChange={(event) => setPos(event.target.value)} />
            <input
              placeholder="中文释义"
              value={definition}
              onChange={(event) => setDefinition(event.target.value)}
              style={{ flex: 1, minWidth: 220 }}
            />
            <button
              className="primary"
              disabled={!headword.trim() || !definition.trim() || create.isPending}
              onClick={() => create.mutate()}
            >
              保存
            </button>
          </div>
          {create.isError && <div className="banner err">{String(create.error)}</div>}
        </div>
      )}

      <div className="toolbar">
        <input
          placeholder="搜索英文或中文释义"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value)
            setOffset(0)
          }}
          style={{ width: 280 }}
        />
        <span className="muted small">第 {offset / PAGE_SIZE + 1} / {Math.max(pages, 1)} 页</span>
        <button className="ghost" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
          上一页
        </button>
        <button
          className="ghost"
          disabled={offset + PAGE_SIZE >= total}
          onClick={() => setOffset(offset + PAGE_SIZE)}
        >
          下一页
        </button>
      </div>

      <div className="split">
        <div className="panel" style={{ padding: 0, overflow: 'hidden' }}>
          <table>
            <thead>
              <tr>
                <th>词</th>
                <th>词性</th>
                <th>释义</th>
                <th>层级</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item: Lexeme) => (
                <tr key={item.id} onClick={() => setSelectedId(item.id)} style={{ cursor: 'pointer' }}>
                  <td className="mono">{item.headword}</td>
                  <td>{item.senses[0]?.pos ?? ''}</td>
                  <td>{item.senses[0]?.definition_zh ?? ''}</td>
                  <td>{item.trait?.main_level ?? <span className="muted">—</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {items.length === 0 && <div className="banner">没有匹配的词条。</div>}
        </div>

        <div className="panel detail">
          {detail.data ? (
            <WordDetail lexeme={detail.data} onDelete={() => remove.mutate(detail.data!.id)} />
          ) : (
            <div className="muted small">选择左侧词条查看详情。</div>
          )}
        </div>
      </div>
    </div>
  )
}

function WordDetail({ lexeme, onDelete }: { lexeme: Lexeme; onDelete: () => void }) {
  const primary = lexeme.senses[0]
  return (
    <div>
      <h3>{lexeme.headword}</h3>
      <div className="ipa">{lexeme.pronunciations[0]?.ipa ?? '—'}</div>
      <div className="small muted">
        {lexeme.kind} · {lexeme.status}
        {lexeme.trait?.main_level && <span className="tag">{lexeme.trait.main_level}</span>}
      </div>

      {lexeme.spellings.length > 0 && (
        <div className="small" style={{ marginTop: 8 }}>
          {lexeme.spellings.map((spelling) => (
            <span key={spelling.id} className="tag muted">
              {spelling.spelling}（{spelling.variant_type}）
            </span>
          ))}
        </div>
      )}

      {lexeme.senses.map((sense) => (
        <div className="sense" key={sense.id}>
          <div>
            <span className="pos">{sense.pos}</span>
            {sense.definition_zh}
          </div>
          {sense.collocations.slice(0, 3).map((collocation) => (
            <div className="ex" key={collocation.id}>
              搭配：{collocation.pattern}
            </div>
          ))}
          {sense.examples.slice(0, 2).map((example) => (
            <div className="ex" key={example.id}>
              {example.text}
            </div>
          ))}
        </div>
      ))}

      {lexeme.etymologies.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <div className="small muted">构词 / 词源（待审核）</div>
          {lexeme.etymologies.map((item) => (
            <div key={item.id} className="small">
              {item.description_zh}
              <span className={'tag ' + (item.status === 'pending_review' ? 'pending' : '')}>
                {item.status}
              </span>
            </div>
          ))}
        </div>
      )}

      <div className="toolbar" style={{ marginTop: 14 }}>
        <button className="danger" onClick={onDelete}>
          归档
        </button>
      </div>
      {primary && <div className="small muted">主释义：{primary.definition_zh}</div>}
    </div>
  )
}
