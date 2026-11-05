import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import cytoscape from 'cytoscape'
import { api } from '../services/api'
import type { GraphEdge, GraphNode } from '../types'

const PALETTE = ['#2f6b4f', '#2d5f8a', '#9a6b12', '#7a4f8a', '#a04638', '#3f7a7a']

const LAYOUT = {
  name: 'cose',
  animate: false,
  padding: 60,
  nodeRepulsion: 12000,
  idealEdgeLength: 95,
  nodeOverlap: 30,
  gravity: 0.55,
  numIter: 1200,
  componentSpacing: 140,
  randomize: false,
} as const

/** Push overlapping nodes apart after the layout settles. */
function spreadNodes(cy: cytoscape.Core, minDistance = 34) {
  const nodes = cy.nodes().toArray()
  for (let iter = 0; iter < 40; iter++) {
    let moved = false
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i]
        const b = nodes[j]
        const pa = a.position()
        const pb = b.position()
        let dx = pb.x - pa.x
        let dy = pb.y - pa.y
        let distance = Math.hypot(dx, dy)
        if (distance < 0.001) {
          dx = 0.6
          dy = 0.6
          distance = 0.85
        }
        if (distance < minDistance) {
          const push = ((minDistance - distance) / distance) * 0.5
          a.position({ x: pa.x - dx * push, y: pa.y - dy * push })
          b.position({ x: pb.x + dx * push, y: pb.y + dy * push })
          moved = true
        }
      }
    }
    if (!moved) break
  }
}

/** Deterministic layout: unit blocks, each root a subtree (root → branches → words). */
function layoutPositions(nodes: GraphNode[], edges: GraphEdge[]) {
  const unitGroups = new Map<string, GraphNode[]>()
  for (const node of nodes) {
    const key = node.unit_id != null ? String(node.unit_id) : 'other'
    const group = unitGroups.get(key) ?? []
    group.push(node)
    unitGroups.set(key, group)
  }
  const edgeBySource = new Map<number, GraphEdge[]>()
  for (const edge of edges) {
    const list = edgeBySource.get(edge.source_node_id) ?? []
    list.push(edge)
    edgeBySource.set(edge.source_node_id, list)
  }

  const keys = [...unitGroups.keys()]
  const unitCols = Math.ceil(Math.sqrt(keys.length))
  const UNIT_CELL = 1100
  const TREE_CELL = 430
  const positions: Record<string, { x: number; y: number }> = {}

  keys.forEach((key, unitIndex) => {
    const list = unitGroups.get(key) ?? []
    const byId = new Map(list.map((node) => [node.id, node]))
    const roots = list.filter((node) => node.node_type === 'root')
    const baseX = (unitIndex % unitCols) * UNIT_CELL
    const baseY = Math.floor(unitIndex / unitCols) * UNIT_CELL
    const treeCols = Math.max(1, Math.ceil(Math.sqrt(Math.max(roots.length, 1))))
    const assigned = new Set<number>()

    const childrenOf = (id: number): GraphNode[] =>
      (edgeBySource.get(id) ?? [])
        .map((edge) => byId.get(edge.target_node_id))
        .filter((node): node is GraphNode => Boolean(node))

    const placeRoot = (root: GraphNode, treeIndex: number) => {
      const tx = baseX + (treeIndex % treeCols) * TREE_CELL
      const ty = baseY + Math.floor(treeIndex / treeCols) * TREE_CELL
      positions[String(root.id)] = { x: tx, y: ty }
      const children = childrenOf(root.id)
      const branches = children.filter((node) => node.node_type === 'branch')
      const directWords = children.filter((node) => node.node_type !== 'branch')
      children.forEach((child) => assigned.add(child.id))

      if (branches.length) {
        branches.forEach((branch, branchIndex) => {
          const angle = (branchIndex / branches.length) * Math.PI * 2 - Math.PI / 2
          const bx = tx + Math.cos(angle) * 92
          const by = ty + Math.sin(angle) * 92
          positions[String(branch.id)] = { x: bx, y: by }
          const words = childrenOf(branch.id)
          words.forEach((word) => assigned.add(word.id))
          const spread = Math.min(2.4, 0.6 * Math.max(words.length, 1))
          words.forEach((word, wordIndex) => {
            const offset =
              words.length === 1 ? 0 : (wordIndex / (words.length - 1) - 0.5) * spread
            const wa = angle + offset
            positions[String(word.id)] = {
              x: bx + Math.cos(wa) * 100,
              y: by + Math.sin(wa) * 100,
            }
          })
        })
      } else {
        directWords.forEach((word, wordIndex) => {
          const angle =
            (wordIndex / Math.max(directWords.length, 1)) * Math.PI * 2 - Math.PI / 2
          positions[String(word.id)] = {
            x: tx + Math.cos(angle) * 100,
            y: ty + Math.sin(angle) * 100,
          }
        })
      }
    }

    roots.forEach((root, index) => placeRoot(root, index))

    const orphans = list.filter(
      (node) => node.node_type !== 'root' && !assigned.has(node.id),
    )
    if (orphans.length) {
      const tx = baseX + (roots.length % treeCols) * TREE_CELL
      const ty = baseY + Math.floor(roots.length / treeCols) * TREE_CELL
      orphans.forEach((word, index) => {
        const angle = (index / Math.max(orphans.length, 1)) * Math.PI * 2 - Math.PI / 2
        positions[String(word.id)] = {
          x: tx + Math.cos(angle) * 100,
          y: ty + Math.sin(angle) * 100,
        }
      })
    }
  })

  return positions
}

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
  const [mode, setMode] = useState<'explore' | 'learning'>('learning')
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
      return nested.flat().sort((a, b) => a.order_no - b.order_no)
    },
  })

  const view = useQuery({
    queryKey: ['graph', mode, unitId],
    queryFn: () =>
      api.graph.view({
        limit: 220,
        unit_id: mode === 'learning' ? unitId : undefined,
      }),
    enabled: mode === 'explore' || Boolean(unitId),
  })

  useEffect(() => {
    if (mode === 'learning' && !unitId && units.data && units.data.length > 0) {
      setUnitId(units.data[0].id)
    }
  }, [mode, unitId, units.data])

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

  const fit = useCallback(() => {
    const cy = cyRef.current
    if (!cy) return
    cy.fit(undefined, 36)
  }, [])

  const zoomBy = useCallback((factor: number) => {
    const cy = cyRef.current
    if (!cy) return
    const level = Math.min(3, Math.max(0.2, cy.zoom() * factor))
    cy.zoom({ level, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } })
  }, [])

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
              'font-size': 11,
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
            style: { width: 34, height: 34, 'font-size': 15, 'font-weight': 700 },
          },
          {
            selector: 'node[type = "branch"]',
            style: { width: 20, height: 20, 'font-size': 11 },
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
        layout: LAYOUT,
        wheelSensitivity: 0.25,
        minZoom: 0.2,
        maxZoom: 3,
        boxSelectionEnabled: false,
        autounselectify: false,
        userPanningEnabled: true,
        userZoomingEnabled: false,
      })
      cyRef.current.on('tap', 'node', (event) => {
        const node = view.data?.nodes.find((item) => String(item.id) === event.target.id())
        setSelected(node ?? null)
      })
      cyRef.current.on('tap', (event) => {
        if (event.target === cyRef.current) {
          setSelected(null)
        }
      })
      const syncLabels = () => {
        const current = cyRef.current
        if (!current) return
        current
          .nodes('[type="word"]')
          .style('text-opacity', 1)
      }
      cyRef.current.on('zoom', syncLabels)
      syncLabels()
    }
    const cy = cyRef.current
    cy.elements().remove()
    cy.add(elements)
    const positions = layoutPositions(view.data?.nodes ?? [], view.data?.edges ?? [])
    cy.layout({ name: 'preset', positions, fit: true, padding: 36, animate: false }).run()
    spreadNodes(cy, 38)
    fit()
  }, [elements, view.data, fit])

  useEffect(() => {
    const cy = cyRef.current
    if (!cy) return
    cy.style()
      .selector('node').style({ color: dark ? '#dfe9e4' : '#1f2a24' })
      .selector('edge').style({ 'line-color': dark ? '#33443f' : '#c3cfc6' })
      .update()
  }, [dark])

  useEffect(() => {
    const element = container.current
    if (!element) return
    const onWheel = (event: WheelEvent) => {
      const cy = cyRef.current
      if (!cy) return
      event.preventDefault()
      const rect = element.getBoundingClientRect()
      const position = { x: event.clientX - rect.left, y: event.clientY - rect.top }
      const factor = Math.exp(-event.deltaY * 0.0036)
      const level = Math.min(3.5, Math.max(0.15, cy.zoom() * factor))
      cy.zoom({ level, renderedPosition: position })
    }
    element.addEventListener('wheel', onWheel, { passive: false })
    return () => element.removeEventListener('wheel', onWheel)
  }, [])

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const cy = cyRef.current
      if (!cy) return
      const tag = (event.target as HTMLElement)?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      const step = 70
      switch (event.key) {
        case 'ArrowLeft':
          cy.panBy({ x: step, y: 0 })
          event.preventDefault()
          break
        case 'ArrowRight':
          cy.panBy({ x: -step, y: 0 })
          event.preventDefault()
          break
        case 'ArrowUp':
          cy.panBy({ x: 0, y: step })
          event.preventDefault()
          break
        case 'ArrowDown':
          cy.panBy({ x: 0, y: -step })
          event.preventDefault()
          break
        case '+':
        case '=':
          zoomBy(1.2)
          event.preventDefault()
          break
        case '-':
        case '_':
          zoomBy(1 / 1.2)
          event.preventDefault()
          break
        case 'r':
        case 'R':
          fit()
          break
        case 'Escape':
          setSelected(null)
          cy.elements().unselect()
          break
        default:
          break
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [fit, zoomBy])

  const selectLearning = () => {
    setMode('learning')
    if (!unitId && units.data && units.data.length > 0) {
      setUnitId(units.data[0].id)
    }
  }

  return (
    <div className={dark ? 'dark' : ''}>
      <div className="page-head">
        <div>
          <h1>知识图谱</h1>
          <p>滚轮缩放 · 拖拽平移 · 方向键移动 · +/- 缩放 · R 复位 · Esc 关闭</p>
        </div>
        <div className="toolbar" style={{ marginBottom: 0 }}>
          <button className={mode === 'explore' ? 'primary' : ''} onClick={() => setMode('explore')}>
            探索
          </button>
          <button className={mode === 'learning' ? 'primary' : ''} onClick={selectLearning}>
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
        <div className="graph-tools">
          <button title="放大（+）" onClick={() => zoomBy(1.2)}>＋</button>
          <button title="缩小（-）" onClick={() => zoomBy(1 / 1.2)}>－</button>
          <button title="复位（R）" onClick={fit}>复位</button>
        </div>
        {selected && (
          <div className="graph-detail">
            <div className="small muted">{selected.node_type}</div>
            <h3 style={{ margin: '2px 0 8px' }}>{selected.label}</h3>
            <div className="small muted">
              关系：
              {view.data?.edges
                .filter((edge) => edge.source_node_id === selected.id || edge.target_node_id === selected.id)
                .slice(0, 8)
                .map((edge) => {
                  const otherId = edge.source_node_id === selected.id ? edge.target_node_id : edge.source_node_id
                  const other = view.data?.nodes.find((node) => node.id === otherId)
                  return `${other?.label ?? otherId}（${edge.relation_type}）`
                })
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
        <span>实线：学习结构</span>
        <span>橙色虚线：待审核派生</span>
        <span>节点大小：词根 &gt; 单词</span>
      </div>
    </div>
  )
}
