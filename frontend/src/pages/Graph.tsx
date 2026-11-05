import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import cytoscape from 'cytoscape'
import { api } from '../services/api'
import type { GraphEdge, GraphNode } from '../types'

const PALETTE = ['#2f6b4f', '#2d5f8a', '#9a6b12', '#7a4f8a', '#a04638', '#3f7a7a']

function colorFor(node: GraphNode, index: number) {
  const meta = node.meta as { fam?: string }
  if (meta?.fam) {
    const keys = ['work', 'stat', 'labor', 'fin', 'volv', 'ergon', 'fallere', 'miht']
    const keyIndex = keys.indexOf(meta.fam)
    return PALETTE[(keyIndex >= 0 ? keyIndex : index) % PALETTE.length]
  }
  return PALETTE[index % PALETTE.length]
}

export default function Graph() {
  const [mode, setMode] = useState<'explore' | 'learning'>('explore')
  const [unitId, setUnitId] = useState<number | undefined>(undefined)
  const [dark, setDark] = useState(false)
  const [selected, setSelected] = useState<GraphNode | null>(null)
  const container = useRef<HTMLDivElement | null>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)

  const units = useQuery({
    queryKey: ['units-all'],
    queryFn: async () => {
      const books = await api.books.list()
      const nested = await Promise.all(books.map((book) => api.books.units(book.id)))
      return nested.flat()
    },
  })

  const view = useQuery({
    queryKey: ['graph', mode, unitId],
    queryFn: () =>
      api.graph.view({
        limit: 220,
        unit_id: mode === 'learning' ? unitId : undefined,
      }),
  })

  const elements = useMemo(() => {
    const data = view.data
    if (!data) return []
    const nodes = data.nodes.map((node, index) => ({
      data: {
        id: String(node.id),
        label: node.label,
        type: node.node_type,
        color: colorFor(node, index),
      },
    }))
    const edges = data.edges.map((edge: GraphEdge) => ({
      data: {
        id: 'e' + edge.id,
        source: String(edge.source_node_id),
        target: String(edge.target_node_id),
        type: edge.relation_type,
        status: edge.status,
      },
    }))
    return [...nodes, ...edges]
  }, [view.data])

  useEffect(() => {
    if (!container.current) return
    if (!cyRef.current) {
      cyRef.current = cytoscape({
        container: container.current,
        elements: [],
        style: [
          {
            selector: 'node',
            style: {
              label: 'data(label)',
              'background-color': 'data(color)',
              color: '#1f2a24',
              'font-size': 10,
              'text-valign': 'bottom',
              'text-margin-y': 4,
              width: 14,
              height: 14,
              'border-width': 2,
              'border-color': '#ffffff',
            },
          },
          {
            selector: 'node[type = "root"]',
            style: { width: 34, height: 34, 'font-size': 14, 'font-weight': 700 },
          },
          {
            selector: 'node[type = "branch"]',
            style: { width: 20, height: 20, 'font-size': 10 },
          },
          {
            selector: 'edge',
            style: {
              width: 1.2,
              'line-color': '#c3cfc6',
              'target-arrow-shape': 'triangle',
              'target-arrow-color': '#c3cfc6',
              'curve-style': 'bezier',
              'arrow-scale': 0.7,
            },
          },
          {
            selector: 'edge[type = "derivation"]',
            style: { 'line-style': 'dashed', 'line-color': '#d9b25f', 'target-arrow-color': '#d9b25f' },
          },
          {
            selector: 'edge[status = "pending_review"]',
            style: { 'line-color': '#c99545', 'target-arrow-color': '#c99545', 'line-style': 'dashed' },
          },
          {
            selector: 'node:selected',
            style: { 'border-color': '#2f6b4f', 'border-width': 3 },
          },
        ],
        layout: { name: 'cose', animate: false, padding: 40 },
        wheelSensitivity: 0.2,
      })
      cyRef.current.on('tap', 'node', (event) => {
        const node = view.data?.nodes.find((item) => String(item.id) === event.target.id())
        setSelected(node ?? null)
      })
    }
    const cy = cyRef.current
    cy.elements().remove()
    cy.add(elements)
    cy.layout({ name: 'cose', animate: false, padding: 40 }).run()
  }, [elements, view.data])

  useEffect(() => {
    const cy = cyRef.current
    if (!cy) return
    cy.style()
      .selector('node').style({ color: dark ? '#dfe9e4' : '#1f2a24' })
      .selector('edge').style({ 'line-color': dark ? '#33443f' : '#c3cfc6' })
      .update()
  }, [dark])

  return (
    <div className={dark ? 'dark' : ''}>
      <div className="page-head">
        <div>
          <h1>知识图谱</h1>
          <p>所有节点与关系来自数据库接口，按需加载</p>
        </div>
        <div className="toolbar" style={{ marginBottom: 0 }}>
          <button className={mode === 'explore' ? 'primary' : ''} onClick={() => setMode('explore')}>
            探索
          </button>
          <button className={mode === 'learning' ? 'primary' : ''} onClick={() => setMode('learning')}>
            学习单元
          </button>
          {mode === 'learning' && (
            <select value={unitId ?? ''} onChange={(event) => setUnitId(Number(event.target.value) || undefined)}>
              <option value="">选择单元</option>
              {(units.data ?? []).map((unit) => (
                <option key={unit.id} value={unit.id}>
                  {unit.title}（{unit.word_count}）
                </option>
              ))}
            </select>
          )}
          <button onClick={() => setDark((value) => !value)}>{dark ? '浅色' : '深色'}</button>
        </div>
      </div>

      {view.isError && <div className="banner err">{String(view.error)}</div>}

      <div className="graph-stage">
        <div ref={container} style={{ width: '100%', height: '100%' }} />
        {selected && (
          <div className="graph-detail">
            <div className="small muted">{selected.node_type}</div>
            <h3 style={{ margin: '2px 0 8px' }}>{selected.label}</h3>
            {selected.lexeme_id && (
              <div className="small">
                词条 ID：<span className="mono">{selected.lexeme_id}</span>
              </div>
            )}
            <div className="small muted">
              关系：
              {view.data?.edges
                .filter((edge) => edge.source_node_id === selected.id || edge.target_node_id === selected.id)
                .slice(0, 8)
                .map((edge) => `${edge.relation_type}(${edge.status})`)
                .join(' · ') || '无'}
            </div>
            <button
              className="ghost small"
              onClick={() => {
                setSelected(null)
                cyRef.current?.elements().unselect()
              }}
            >
              关闭
            </button>
          </div>
        )}
      </div>
      <div className="legend" style={{ marginTop: 10 }}>
        <span><i style={{ background: '#2f6b4f' }} />词根/工作</span>
        <span><i style={{ background: '#2d5f8a' }} />stat 族</span>
        <span><i style={{ background: '#9a6b12' }} />labor 族</span>
        <span><i style={{ background: '#d9b25f' }} />派生（待审核）</span>
      </div>
    </div>
  )
}
