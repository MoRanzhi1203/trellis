import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import cytoscape from 'cytoscape'
import { api } from '../services/api'
import type { GraphEdge, GraphNode } from '../types'


type SelectedEdge = {
  id: string
  source: string
  target: string
  type: string
  status: string
  rel: string
}

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
      children.forEach((child) => assigned.add(child.id))
      const words: GraphNode[] = []
      if (branches.length) {
        branches.forEach((branch) => {
          assigned.add(branch.id)
          childrenOf(branch.id).forEach((word) => {
            assigned.add(word.id)
            words.push(word)
          })
        })
      } else {
        children
          .filter((node) => node.node_type !== 'branch')
          .forEach((word) => words.push(word))
      }
      const spread = Math.min(2.4, 0.6 * Math.max(words.length, 1))
      words.forEach((word, wordIndex) => {
        const offset =
          words.length === 1 ? 0 : (wordIndex / (words.length - 1) - 0.5) * spread
        const angle = -Math.PI / 2 + offset
        positions[String(word.id)] = {
          x: tx + Math.cos(angle) * 110,
          y: ty + Math.sin(angle) * 110,
        }
      })
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

/** Layered layout: roots → branches → words from left to right. */
function layoutLayered(nodes: GraphNode[], edges: GraphEdge[]) {
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

  const positions: Record<string, { x: number; y: number }> = {}
  let unitOffsetX = 0
  for (const list of unitGroups.values()) {
    const byId = new Map(list.map((node) => [node.id, node]))
    const roots = list.filter((node) => node.node_type === 'root')
    const childrenOf = (id: number) =>
      (edgeBySource.get(id) ?? [])
        .map((edge) => byId.get(edge.target_node_id))
        .filter((node): node is GraphNode => Boolean(node))

    let cursorY = 0
    for (const root of roots) {
      positions[String(root.id)] = { x: unitOffsetX, y: cursorY }
      const kids = childrenOf(root.id)
      const branches = kids.filter((node) => node.node_type === 'branch')
      const words = branches.length
        ? branches.flatMap((branch) => childrenOf(branch.id))
        : kids.filter((node) => node.node_type !== 'branch')
      words.forEach((word, index) => {
        positions[String(word.id)] = {
          x: unitOffsetX + 320,
          y: cursorY + index * 34,
        }
      })
      cursorY += Math.max(70, words.length * 34 + 24) + 90
    }
    unitOffsetX += 900
  }
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
  const params = new URLSearchParams(window.location.search)
  const [mode, setMode] = useState<'explore' | 'learning'>(
    params.get('mode') === 'explore' ? 'explore' : 'learning',
  )
  const [unitId, setUnitId] = useState<number | undefined>(undefined)
  const [dark, setDark] = useState(params.get('dark') === '1')
  const [selected, setSelected] = useState<GraphNode | null>(null)
  const [selectedEdge, setSelectedEdge] = useState<SelectedEdge | null>(null)
  const [showAux, setShowAux] = useState(params.get('aux') === '1')
  const [layoutMode, setLayoutMode] = useState<'grouped' | 'layered'>(
    params.get('layout') === 'layered' ? 'layered' : 'grouped',
  )
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set())
  const [search, setSearch] = useState('')
  const [relationFilter, setRelationFilter] = useState<
    'all' | 'learning' | 'semantic' | 'derivation' | 'pending'
  >('all')
  const [viewMode, setViewMode] = useState<'local' | 'global'>(
    params.get('view') === 'global' ? 'global' : 'local',
  )
  const [centerId, setCenterId] = useState<number | null>(null)
  const [history, setHistory] = useState<number[]>([])
  const [depth, setDepth] = useState(1)
  const container = useRef<HTMLDivElement | null>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)
  const viewRef = useRef<{ nodes: GraphNode[]; edges: GraphEdge[] } | null>(null)
  const centerRef = useRef<number | null>(null)
  centerRef.current = centerId

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

  const localView = useQuery({
    queryKey: ['graph-local', centerId, depth],
    queryFn: () =>
      api.graph.view({ node_id: centerId ?? undefined, depth: depth + 1, limit: 200 }),
    enabled: viewMode === 'local' && centerId != null,
  })

  useEffect(() => {
    if (viewMode !== 'local' || centerId != null || !view.data) return
    const root = view.data.nodes.find((node) => node.node_type === 'root')
    if (root) setCenterId(root.id)
  }, [viewMode, centerId, view.data])

  useEffect(() => {
    const target = params.get('select')
    if (!target || !view.data) return
    const node = view.data.nodes.find(
      (item) => String(item.id) === target || String(item.lexeme_id) === target,
    )
    if (node) setSelected(node)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view.data])

  viewRef.current = view.data ?? null

  const rootOwners = useMemo(() => {
    const data = view.data
    const owners = new Map<number, number>()
    if (!data) return owners
    const children = new Map<number, number[]>()
    data.edges.forEach((edge) => {
      const list = children.get(edge.source_node_id) ?? []
      list.push(edge.target_node_id)
      children.set(edge.source_node_id, list)
    })
    const roots = data.nodes.filter((node) => node.node_type === 'root')
    for (const root of roots) {
      const stack = [root.id]
      while (stack.length) {
        const current = stack.pop() as number
        for (const child of children.get(current) ?? []) {
          if (!owners.has(child)) {
            owners.set(child, root.id)
            stack.push(child)
          }
        }
      }
    }
    return owners
  }, [view.data])

  const elements = useMemo(() => {
    const data = viewMode === 'local' ? localView.data : view.data
    if (!data) return []
    const branchIds = new Set(
      data.nodes.filter((node) => node.node_type === 'branch').map((node) => node.id),
    )
    const branchParent = new Map<number, number>()
    data.edges.forEach((edge) => {
      if (branchIds.has(edge.target_node_id)) {
        branchParent.set(edge.target_node_id, edge.source_node_id)
      }
    })
    const nodes = data.nodes
      .filter((node) => !branchIds.has(node.id))
      .map((node, index) => ({
        data: {
          id: String(node.id),
          label: node.label,
          type: node.node_type,
          color: colorFor(node, index),
        },
      }))
    const edges: Array<{
      data: { id: string; source: string; target: string; type: string; status: string; rel: string }
    }> = []
    data.edges.forEach((edge) => {
      if (branchIds.has(edge.target_node_id)) return
      let source = edge.source_node_id
      if (branchIds.has(source)) {
        const parent = branchParent.get(source)
        if (parent == null) return
        source = parent
      }
      const allowed =
        relationFilter === 'pending'
          ? edge.status === 'pending_review'
          : relationFilter !== 'all'
            ? edge.relation_type === relationFilter
            : showAux || edge.relation_type === 'learning'
      if (!allowed) return
      edges.push({
        data: {
          id: 'e' + edge.id,
          source: String(source),
          target: String(edge.target_node_id),
          type: edge.relation_type,
          status: edge.status,
          rel: edge.evidence || '',
        },
      })
    })
    return [...nodes, ...edges]
  }, [view.data, localView.data, viewMode, showAux, relationFilter])

  const wordDetail = useQuery({
    queryKey: ['graph-word', selected?.lexeme_id],
    queryFn: () => api.words.get(selected?.lexeme_id as number),
    enabled: Boolean(selected?.lexeme_id),
  })

  const labelOf = (nodeId: string) => {
    const node = view.data?.nodes.find((item) => String(item.id) === nodeId)
    return node?.label ?? nodeId
  }

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
            style: { width: 36, height: 36, 'font-size': 15, 'font-weight': 700 },
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
              label: 'data(rel)',
              'font-size': 8,
              color: '#5b6b62',
              'text-rotation': 'none',
              'text-background-color': '#ffffff',
              'text-background-opacity': 0.85,
              'text-background-padding': '2px',
              'text-opacity': 0,
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
          {
            selector: '.dimmed',
            style: { opacity: 0.15 },
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
        const data = viewRef.current
        const node = data?.nodes.find((item) => String(item.id) === event.target.id())
        if (!node) return
        setSelected(node)
        setSelectedEdge(null)
        const cyInstance = cyRef.current
        if (cyInstance) {
          cyInstance.elements().removeClass('dimmed focused')
          const el = cyInstance.getElementById(String(node.id))
          el.addClass('focused')
          el.neighborhood().addClass('focused')
          cyInstance.elements().not(el).not(el.neighborhood()).addClass('dimmed')
        }
      })
      cyRef.current.on('dbltap', 'node', (event) => {
        const id = Number(event.target.id())
        if (Number.isNaN(id)) return
        const current = centerRef.current
        if (current != null && current !== id) {
          setHistory((prev) => [...prev, current])
        }
        setCenterId(id)
      })
      cyRef.current.on('tap', 'edge', (event) => {
        const edgeData = event.target.data()
        setSelected(null)
        setSelectedEdge({
          id: edgeData.id,
          source: edgeData.source,
          target: edgeData.target,
          type: edgeData.type,
          status: edgeData.status,
          rel: edgeData.rel,
        })
        const cyInstance = cyRef.current
        if (cyInstance) {
          cyInstance.elements().removeClass('dimmed focused')
          const el = cyInstance.getElementById(edgeData.id)
          el.addClass('focused')
          el.connectedNodes().addClass('focused')
        }
      })
      cyRef.current.on('tap', (event) => {
        if (event.target === cyRef.current) {
          setSelected(null)
          setSelectedEdge(null)
          cyRef.current?.elements().removeClass('dimmed focused')
        }
      })
      const syncLabels = () => {
        const current = cyRef.current
        if (!current) return
        current
          .nodes('[type="word"]')
          .style('text-opacity', current.zoom() > 0.45 ? 1 : 0)
        current.edges().style('text-opacity', current.zoom() > 0.7 ? 1 : 0)
      }
      cyRef.current.on('zoom', syncLabels)
      syncLabels()
    }
    const cy = cyRef.current
    cy.elements().remove()
    cy.add(elements)
    if (viewMode === 'local') {
      const nodes = (localView.data?.nodes ?? [])
      const positions: Record<string, { x: number; y: number }> = {}
      let ringIndex = 0
      for (const node of nodes) {
        if (node.id === centerId) {
          positions[String(node.id)] = { x: 0, y: 0 }
        } else {
          const angle = (ringIndex / Math.max(1, nodes.length - 1)) * Math.PI * 2
          const radius = 170 + (ringIndex % 4) * 34
          positions[String(node.id)] = {
            x: Math.cos(angle) * radius,
            y: Math.sin(angle) * radius,
          }
          ringIndex += 1
        }
      }
      cy.layout({ name: 'preset', positions, fit: true, padding: 60, animate: false }).run()
      spreadNodes(cy, 76)
      cy.fit(undefined, 60)
    } else {
      const layoutFn = layoutMode === 'layered' ? layoutLayered : layoutPositions
      const positions = layoutFn(view.data?.nodes ?? [], view.data?.edges ?? [])
      cy.layout({ name: 'preset', positions, fit: true, padding: 36, animate: false }).run()
      spreadNodes(cy, 38)
      fit()
    }
  }, [elements, view.data, localView.data, viewMode, centerId, fit, layoutMode])

  useEffect(() => {
    const cy = cyRef.current
    const data = view.data
    if (!cy || !data) return
    for (const node of data.nodes) {
      const el = cy.getElementById(String(node.id))
      if (!el.length) continue
      const owner = rootOwners.get(node.id)
      const hidden = owner != null && collapsed.has(owner)
      el.style('display', hidden ? 'none' : 'element')
    }
  }, [collapsed, view.data, rootOwners])

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

  const goBack = () => {
    if (!history.length) return
    const last = history[history.length - 1]
    setHistory(history.slice(0, -1))
    setCenterId(last)
  }

  const setCenterFromSelected = () => {
    if (!selected) return
    setHistory((prev) => [...prev, centerId ?? selected.id])
    setCenterId(selected.id)
  }

  const locate = () => {
    const cy = cyRef.current
    const data = view.data
    const query = search.trim().toLowerCase()
    if (!cy || !data || !query) return
    const hit = data.nodes.find((node) => node.label.toLowerCase().includes(query))
    if (!hit) return
    const owner = rootOwners.get(hit.id)
    if (owner != null && collapsed.has(owner)) {
      setCollapsed((prev) => {
        const next = new Set(prev)
        next.delete(owner)
        return next
      })
    }
    const el = cy.getElementById(String(hit.id))
    el.select()
    cy.animate({ center: { eles: el }, zoom: Math.max(cy.zoom(), 1) }, { duration: 300 })
    setSelected(hit)
  }

  const collapseAll = () => {
    const data = view.data
    if (!data) return
    setCollapsed(
      new Set(
        data.nodes.filter((node) => node.node_type === 'root').map((node) => node.id),
      ),
    )
  }

  return (
    <div className={dark ? 'dark' : ''}>
      <div className="page-head">
        <div>
          <h1>知识图谱</h1>
          <p>滚轮缩放 · 拖拽平移 · 方向键移动 · +/- 缩放 · R 复位 · Esc 关闭</p>
        </div>
        <div className="toolbar" style={{ marginBottom: 0 }}>
          <button className={mode === 'learning' ? 'primary' : ''} onClick={selectLearning}>
            学习单元
          </button>
          <button className={mode === 'explore' ? 'primary' : ''} onClick={() => setMode('explore')}>
            探索
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
          <button
            className={layoutMode === 'grouped' ? 'primary' : ''}
            onClick={() => setLayoutMode('grouped')}
          >
            分组
          </button>
          <button
            className={layoutMode === 'layered' ? 'primary' : ''}
            onClick={() => setLayoutMode('layered')}
          >
            层级
          </button>
          <button onClick={() => setDark((value) => !value)}>{dark ? '浅色' : '深色'}</button>
        </div>
      </div>

      <div className="toolbar" style={{ marginTop: -4 }}>
        <button
          className={viewMode === 'local' ? 'primary' : ''}
          onClick={() => setViewMode('local')}
        >
          局部
        </button>
        <button
          className={viewMode === 'global' ? 'primary' : ''}
          onClick={() => setViewMode('global')}
        >
          全局
        </button>
        {viewMode === 'local' && (
          <>
            <select value={depth} onChange={(event) => setDepth(Number(event.target.value))}>
              <option value={1}>1 跳</option>
              <option value={2}>2 跳</option>
              <option value={3}>3 跳</option>
            </select>
            <button onClick={goBack} disabled={history.length === 0}>
              返回
            </button>
            <button onClick={setCenterFromSelected} disabled={!selected}>
              设为中心
            </button>
          </>
        )}
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') locate()
          }}
          placeholder="搜索单词或词根，回车定位"
          style={{ width: 240 }}
        />
        <select
          value={relationFilter}
          onChange={(event) => setRelationFilter(event.target.value as typeof relationFilter)}
        >
          <option value="all">学习关系（默认）</option>
          <option value="learning">仅学习结构</option>
          <option value="semantic">语义关联</option>
          <option value="derivation">派生关系</option>
          <option value="pending">待审核</option>
        </select>
        <button onClick={collapseAll}>折叠全部词根</button>
        <button onClick={() => setCollapsed(new Set())}>展开全部</button>
        <button
          className={showAux ? 'primary' : ''}
          onClick={() => setShowAux((value) => !value)}
          title="语义、派生与待审核关系默认隐藏"
        >
          {showAux ? '隐藏辅助关系' : '显示辅助关系'}
        </button>
      </div>

      {view.isError && <div className="banner err">{String(view.error)}</div>}

      <div className="graph-stage">
        <div ref={container} style={{ width: '100%', height: '100%' }} />
        <div className="graph-tools">
          <button title="放大（+）" onClick={() => zoomBy(1.2)}>＋</button>
          <button title="缩小（-）" onClick={() => zoomBy(1 / 1.2)}>－</button>
          <button title="复位（R）" onClick={fit}>复位</button>
        </div>
        {selectedEdge && (
          <div className="graph-detail">
            <div className="small muted">构词关系</div>
            <h3 style={{ margin: '2px 0 8px' }}>
              {labelOf(selectedEdge.source)} → {labelOf(selectedEdge.target)}
            </h3>
            <div className="small">类型：{selectedEdge.type}</div>
            {selectedEdge.rel && (
              <div className="small">
                操作：<span className="mono">{selectedEdge.rel}</span>
              </div>
            )}
            <div className="small muted">审核：{selectedEdge.status}</div>
            <button
              className="ghost small"
              onClick={() => {
                setSelectedEdge(null)
                cyRef.current?.elements().removeClass('focused dimmed')
              }}
            >
              关闭
            </button>
          </div>
        )}
        {selected && (
          <div className="graph-detail">
            <div className="small muted">{selected.node_type === 'root' ? '词根' : '单词'}</div>
            <h3 style={{ margin: '2px 0 8px' }}>{selected.label}</h3>
            {selected.lexeme_id && wordDetail.data && (
              <>
                {wordDetail.data.pronunciations.length > 0 && (
                  <div className="ipa">{wordDetail.data.pronunciations[0].ipa}</div>
                )}
                {wordDetail.data.senses.map((sense) => (
                  <div key={sense.id} className="sense">
                    <span className="pos">{sense.pos}</span>
                    {sense.definition_zh}
                  </div>
                ))}
                {wordDetail.data.trait?.main_level && (
                  <div className="small muted">层级：{wordDetail.data.trait.main_level}</div>
                )}
                {wordDetail.data.etymologies.map((item) => (
                  <div key={item.id} className="small">
                    构词：{item.description_zh}
                    <span className={'tag ' + (item.status === 'pending_review' ? 'pending' : '')}>
                      {item.status}
                    </span>
                  </div>
                ))}
              </>
            )}
            {selected.node_type === 'root' ? (
              <div className="small">
                派生词：
                {(view.data?.nodes ?? [])
                  .filter(
                    (node) => node.node_type === 'word' && rootOwners.get(node.id) === selected.id,
                  )
                  .map((node) => node.label)
                  .join(' · ') || '无'}
              </div>
            ) : (
              <div className="small">
                {(() => {
                  const ownerId = rootOwners.get(selected.id)
                  const owner = view.data?.nodes.find((node) => node.id === ownerId)
                  const formation = view.data?.edges.find(
                    (edge) => edge.target_node_id === selected.id,
                  )?.evidence
                  return (
                    <>
                      {owner && <div className="muted">词根：{owner.label}</div>}
                      {formation && (
                        <div>
                          构词：<span className="mono">{formation}</span>
                        </div>
                      )}
                    </>
                  )
                })()}
              </div>
            )}
            <button
              className="ghost small"
              onClick={() => {
                setSelected(null)
                cyRef.current?.elements().removeClass('dimmed focused')
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
