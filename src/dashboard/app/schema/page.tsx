'use client'
import { useEffect, useState, useCallback, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Sidebar from '../../components/Sidebar'
import { getGraphSchema, getNodesByType, getNodeEdges, getEgoGraph } from '../../lib/api'
import EgoGraph from '../../components/EgoGraph'

const GROUP_SORT_ORDER: Record<string, string[]> = {
  Law: [
    'DSGVO', 'EU AI Act', 'NIS2', 'CRA', 'DSA', 'DORA',
    'DDG', 'TTDSG', 'BGB', 'UWG', 'PAngV',
    'UK_GDPR',
  ],
  Control: [],
}

function sortGroups(groups: Record<string, NodeProps[]>, nodeType: string): [string, NodeProps[]][] {
  const entries = Object.entries(groups)
  const priority = GROUP_SORT_ORDER[nodeType] || []

  if (nodeType === 'Control') {
    return entries.sort((a, b) => b[1].length - a[1].length)
  }

  return entries.sort((a, b) => {
    const ai = priority.indexOf(a[0])
    const bi = priority.indexOf(b[0])
    if (ai === -1 && bi === -1) return a[0].localeCompare(b[0])
    if (ai === -1) return 1
    if (bi === -1) return -1
    return ai - bi
  })
}

const EDGE_EXPLANATIONS: Record<string, { out: string; in: string }> = {
  BASED_ON:             { out: 'Documents generated from this',         in: 'Nodes that are based on this' },
  IMPLEMENTS:           { out: 'This technically implements',            in: 'Controls implementing this' },
  REQUIRES:             { out: 'Makes the following mandatory',          in: 'Services/nodes requiring this' },
  REQUIRES_MECHANISM:   { out: 'Data transfers require this mechanism',  in: 'Triggered by' },
  REQUIRES_COMPLIANCE:  { out: 'Requires compliance with',               in: 'Services requiring this' },
  LOCATED_IN:           { out: 'Operated from',                          in: 'Services located here' },
  MAY_REQUIRE:          { out: 'May apply for this sector',              in: 'Triggered by' },
  SUPERSEDES:           { out: 'This replaces',                          in: 'Superseded by' },
  MAPS_TO:              { out: 'Maps to equivalent control',             in: 'Mapped from' },
  REFERENCES:           { out: 'References',                             in: 'Referenced by' },
  TRIGGERS:             { out: 'Triggers generation of',                 in: 'Triggered by' },
  REQUIRES_CONTROL:     { out: 'Requires this control',                  in: 'Services requiring this control' },
}

const PROP_LABELS: Record<string, string> = {
  dsgvo_article:          'GDPR article',
  valid_from:             'Valid from',
  applies_from:           'Applies from',
  source_pdf:             'Source document',
  last_verified:          'Last verified',
  text_updated:           'Last updated',
  default_tom_measure:    'Default TOM measure',
  regulation:             'Regulation',
  jurisdictions:          'Jurisdictions',
  eu_ai_act:              'EU AI Act reference',
  processing_purpose:     'Processing purpose',
  data_categories:        'Data categories',
  data_subjects:          'Data subjects',
  deletion_period:        'Retention period',
  legal_basis:            'Legal basis',
  dpa_required:           'DPA required',
  dpa_url:                'DPA URL',
  gdpr_adequate:          'GDPR adequate',
  requires_sccs:          'SCCs required',
  framework:              'Framework',
  version:                'Version',
  article:                'Article',
  short:                  'Short reference',
  sector:                 'Sector',
  note_de:                'Note (DE)',
  note_en:                'Note (EN)',
  copyright_note:         'Copyright',
  translation_confidence_de: 'DE translation confidence',
  translation_confidence_en: 'EN translation confidence',
  anforderungen_basis:    'Basis requirements',
  anforderungen_standard: 'Standard requirements',
  basis_requirements:     'Basis requirements',
  dsgvo_art32:            'GDPR Art. 32 reference',
  tom_relevance:          'TOM relevance',
  area:                   'Area',
  categories:             'Categories',
  subcategories:          'Subcategories',
  source_file:            'Source file',
  in_force:               'In force',
  description:            'Description',
}

// One line per node type — rendered as a subline in the registry so the
// vocabulary explains itself (finding 2026-07-19: descriptions existed but
// were never rendered; 10 types were missing, 3 entries were stale/wrong).
const NODE_TYPE_META: Record<string, { icon: string; description: string }> = {
  Service:              { icon: '◫', description: 'Third-party processors — Stripe, AWS, Supabase…' },
  Control:              { icon: '◈', description: 'Technical controls: BSI IT-Grundschutz, NIST CSF, OWASP' },
  Measure:              { icon: '▤', description: 'TOM measures from the SDM catalogue (DSK Standard Data Protection Model)' },
  Law:                  { icon: '⚖', description: 'GDPR, EU AI Act, NIS2, CRA articles with enforcement dates' },
  Requirement:          { icon: '▣', description: 'BSI IT-Grundschutz basic requirements per building block' },
  ServiceCategory:      { icon: '⊞', description: 'Category layer linking services to their controls' },
  Requirement_B:        { icon: '▥', description: 'SDM building-block requirements, mapped to GDPR articles' },
  UseCase:              { icon: '◯', description: 'AI system categories with EU AI Act risk classification' },
  DocumentType:         { icon: '◻', description: 'Generated documents: AVV, TOM, VVT, DSFA, AI Act Manifest…' },
  SupervisoryAuthority: { icon: '⚑', description: 'German data protection authorities (federal + states)' },
  HostingProvider:      { icon: '☁', description: 'Curated hosting providers with certifications and regions' },
  ProcessingActivity:   { icon: '⚙', description: 'Standard processing activities for the records of processing' },
  Country:              { icon: '◉', description: 'Jurisdictions with GDPR adequacy status' },
  DataSubject:          { icon: '◔', description: 'Categories of affected persons (customers, employees…)' },
  LegalBasis:           { icon: '§', description: 'GDPR Art. 6 legal bases for processing' },
  ProtectionGoal:       { icon: '⬡', description: 'SDM protection goals (transparency, integrity, intervenability…)' },
  RiskLevel:            { icon: '▸', description: 'EU AI Act risk classes: Prohibited / High / Limited / Minimal / GPAI' },
  RetentionPeriod:      { icon: '◷', description: 'Retention periods applied in generated documents' },
  Risk:                 { icon: '▲', description: 'AI privacy risks the pipeline guards against (PII in LLM context…)' },
  TransferMechanism:    { icon: '⇄', description: 'Third-country transfer safeguards: SCCs, adequacy, BCRs' },
}

type SchemaEntry = { label: string; count: number }
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type NodeProps = Record<string, any>

function getNodeDisplayId(props: NodeProps): string {
  return String(props.id || props.name || props.type || props.level || Object.values(props)[0] || '—')
}

function getNodeDisplayTitle(props: NodeProps): string {
  // i18n: prefer EN as primary display, DE as fallback (ADR-047)
  return String(props.title_en || props.title_de || props.description || '')
}

function getGroupKey(props: NodeProps): string {
  return String(props.name || props.framework || '')
}

function SeverityBadge({ value }: { value: string }) {
  const cfg: Record<string, { bg: string; color: string }> = {
    high:   { bg: 'rgba(248,113,113,0.15)', color: 'var(--state-fail)' },
    medium: { bg: 'rgba(245,158,11,0.15)',  color: 'var(--state-warn)' },
    low:    { bg: 'rgba(74,222,128,0.15)',  color: 'var(--state-pass)' },
  }
  const s = cfg[value?.toLowerCase()] || cfg.medium
  return (
    <span style={{
      padding: '2px 8px', borderRadius: '10px', fontSize: '11px',
      fontWeight: 600, background: s.bg, color: s.color,
      fontFamily: 'ui-monospace, monospace',
    }}>
      {value?.toUpperCase()}
    </span>
  )
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function buildContextSummary(nodeType: string, props: NodeProps, edges: any[]): string | null {
  const outEdges = edges.filter(e => e.direction === 'out')
  const inEdges  = edges.filter(e => e.direction === 'in')

  const docTypes = outEdges
    .filter(e => e.target_type === 'DocumentType')
    .map(e => e.target_id).join(', ')

  const services = inEdges
    .filter(e => e.source_type === 'Service')
    .map(e => e.source_id)
  const serviceCount = services.length
  const serviceList  = services.slice(0, 3).join(', ')

  const controls = inEdges.filter(e => e.source_type === 'Control')
  const controlCount = controls.length

  switch (nodeType) {
    case 'Law': {
      const parts = [
        serviceCount > 0
          ? `Services like **${serviceList}${serviceCount > 3 ? ` and ${serviceCount - 3} more` : ''}** trigger this article.`
          : null,
        docTypes
          ? `It mandates the following documents: **${docTypes}**.`
          : null,
        controlCount > 0
          ? `**${controlCount} controls** (ISO 27001, BSI, OWASP) technically implement what this article legally requires.`
          : null,
        // Fallback: note/description — EN-first with DE fallback (ADR-047,
        // same pattern getNodeDisplayTitle already uses on this page).
        (serviceCount === 0 && controlCount === 0 && !docTypes && (props.note_en || props.note))
          ? (props.note_en || props.note)
          : null,
        (serviceCount === 0 && controlCount === 0 && !docTypes && !(props.note_en || props.note) && (props.description_en || props.description))
          ? (props.description_en || props.description)
          : null,
        props.applies_from
          ? `In force since **${props.applies_from}**.`
          : null,
      ].filter(Boolean)
      return parts.length > 0 ? parts.join(' ') : null
    }
    case 'Control': {
      const laws = outEdges
        .filter(e => e.target_type === 'Law')
        .map(e => e.target_id).join(', ')
      return [
        props.framework ? `This control is part of **${props.framework}**.` : null,
        laws ? `It technically implements **${laws}**.` : null,
        (props.default_tom_measure_en || props.default_tom_measure)
          ? `Default TOM measure: ${String(props.default_tom_measure_en || props.default_tom_measure).slice(0, 120)}${String(props.default_tom_measure_en || props.default_tom_measure).length > 120 ? '...' : ''}`
          : null,
        props.severity === 'critical'
          ? `⚠ Severity is **CRITICAL** — non-compliance directly violates ${props.dsgvo_article ? `GDPR Art. ${props.dsgvo_article}` : 'applicable law'}.`
          : null,
      ].filter(Boolean).join(' ')
    }
    case 'Service': {
      const requiredDocs = outEdges
        .filter(e => e.target_type === 'DocumentType')
        .map(e => e.target_id).join(', ')
      const country = props.country || props.jurisdictions
      return [
        country ? `**${props.name}** is operated from **${country}**.` : null,
        props.gdpr_adequate === false
          ? `The country has **no GDPR adequacy decision** — Standard Contractual Clauses (SCCs) are required.`
          : null,
        requiredDocs ? `Using this service mandates: **${requiredDocs}**.` : null,
        props.dpa_url ? `DPA available at ${props.dpa_url}` : null,
      ].filter(Boolean).join(' ')
    }
    case 'DocumentType': {
      const basedOn = outEdges
        .filter(e => e.target_type === 'Law')
        .map(e => e.target_id).join(', ')
      const sections = Array.isArray(props.required_sections) ? props.required_sections.length : 0
      return [
        basedOn ? `This document type is grounded in **${basedOn}**.` : null,
        sections > 0 ? `Contains **${sections} mandatory sections** defined by the graph.` : null,
        `Generated automatically when the scanner detects a qualifying service or use case.`,
      ].filter(Boolean).join(' ')
    }
    case 'TransferMechanism':
      return `Required for data transfers to countries without a GDPR adequacy decision. Legal basis: **${props.legal_basis || 'GDPR Art. 46'}**.`
    case 'Country':
      return props.gdpr_adequate === false
        ? `**${props.name}** has no GDPR adequacy decision. Any service operated from here requires **SCCs** and a Transfer Impact Assessment (TIA).`
        : `**${props.name}** has a GDPR adequacy decision — data transfers are permitted without additional safeguards.`
    default:
      return null
  }
}

function ContextCard({ text }: { text: string }) {
  const html = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  return (
    <div style={{
      background: 'rgba(74,143,255,0.05)',
      border: '1px solid rgba(74,143,255,0.18)',
      borderLeft: '3px solid var(--accent)',
      borderRadius: '6px',
      padding: '14px 16px',
      marginBottom: '18px',
    }}>
      <div style={{
        fontSize: '9px',
        color: 'var(--accent)',
        letterSpacing: '0.1em',
        fontWeight: 600,
        marginBottom: '8px',
        fontFamily: 'ui-monospace, monospace',
      }}>
        WHY THIS MATTERS
      </div>
      <p
        dangerouslySetInnerHTML={{ __html: html }}
        style={{
          fontSize: '12px',
          color: 'var(--text-secondary)',
          lineHeight: '1.65',
          fontFamily: 'Inter, system-ui, sans-serif',
          margin: 0,
        }}
      />
    </div>
  )
}

function EdgeGroup({
  direction, rel, targetType, edgeNodes, explanation, onNodeClick,
}: {
  direction: 'out' | 'in'
  rel: string
  targetType: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  edgeNodes: any[]
  explanation: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onNodeClick: (edge: any) => void
}) {
  const [expanded, setExpanded] = useState(edgeNodes.length <= 5)

  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border-default)',
      borderRadius: '5px',
      overflow: 'hidden',
      marginBottom: '6px',
    }}>
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          padding: '9px 12px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          cursor: 'pointer',
          transition: 'background 120ms ease',
        }}
        onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-elevated)' }}
        onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
      >
        <span style={{ fontSize: '10px', color: 'var(--text-muted)', width: '14px' }}>
          {direction === 'out' ? '→' : '←'}
        </span>
        <span style={{ fontSize: '10px', color: 'var(--accent)', fontWeight: 600, letterSpacing: '0.04em' }}>
          {rel}
        </span>
        <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
          {direction === 'out' ? '→' : '←'} [{targetType}]
        </span>
        <span style={{
          fontSize: '11px',
          color: 'var(--text-muted)',
          flex: 1,
          fontFamily: 'Inter, system-ui, sans-serif',
          fontStyle: 'italic',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}>
          {explanation}
        </span>
        <span style={{ fontSize: '10px', color: 'var(--accent)', flexShrink: 0 }}>
          {edgeNodes.length} {expanded ? '▼' : '▶'}
        </span>
      </div>

      {expanded && (
        <div style={{ padding: '4px 12px 10px 32px', display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
          {edgeNodes.map((edge, i) => {
            // Use human-readable label if available, fall back to ID
            const label = direction === 'out'
              ? (edge.target_label || edge.target_id || '?')
              : (edge.source_label || edge.source_id || '?')
            if (!label || label === 'null' || label === 'undefined' || label === '?') return null
            return (
              <span
                key={i}
                onClick={() => onNodeClick(edge)}
                style={{
                  fontSize: '11px',
                  color: 'var(--accent)',
                  padding: '2px 8px',
                  background: 'rgba(74,143,255,0.08)',
                  borderRadius: '3px',
                  border: '1px solid rgba(74,143,255,0.2)',
                  cursor: 'pointer',
                  fontFamily: 'ui-monospace, monospace',
                  transition: 'background 100ms',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(74,143,255,0.15)' }}
                onMouseLeave={e => { e.currentTarget.style.background = 'rgba(74,143,255,0.08)' }}
              >
                {label}
              </span>
            )
          })}
        </div>
      )}
    </div>
  )
}

function SchemaPageInner() {
const searchParams = useSearchParams()
const router = useRouter()
const [schema, setSchema] = useState<SchemaEntry[]>([])
const [selectedType, setSelectedType] = useState<string>(searchParams.get('type') || 'Control')
const [nodes, setNodes] = useState<NodeProps[]>([])
  // Visible error state — a failed nodes fetch must NOT render as "0 nodes"
  // (allowlist-drift finding 2026-07-19: 400s were masked as empty lists).
  const [nodesError, setNodesError] = useState(false)
const [selectedNode, setSelectedNode] = useState<NodeProps | null>(null)
const [edges, setEdges] = useState<{ direction: string; rel: string; target_type?: string; target_id?: string; source_type?: string; source_id?: string }[]>([])
const [search, setSearch] = useState('')
const [loading, setLoading] = useState(true)
const [loadingNodes, setLoadingNodes] = useState(false)
const [loadingEdges, setLoadingEdges] = useState(false)
const [textExpanded, setTextExpanded] = useState(false)
const [navHistory, setNavHistory] = useState<Array<{type: string, node: NodeProps}>>([]) 
const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set())
const [showGraph, setShowGraph] = useState(false)
const [showRaw, setShowRaw] = useState(false)
const [egoGraph, setEgoGraph] = useState<{ nodes: any[]; edges: any[]; center_id: string } | null>(null)
const [loadingGraph, setLoadingGraph] = useState(false)
  // URL param: ?node=Stripe to auto-select a node after type loads
  const urlNode = searchParams.get('node')

  // Update URL bar without full navigation
  const updateUrl = useCallback((type: string, nodeId?: string) => {
    const params = new URLSearchParams()
    params.set('type', type)
    if (nodeId) params.set('node', nodeId)
    router.replace(`/schema?${params.toString()}`, { scroll: false })
  }, [router])

  const handleEdgeClick = useCallback(async (edge: { direction: string; rel?: string; target_type?: string; target_id?: string; source_type?: string; source_id?: string }) => {
    const targetType = edge.direction === 'out' ? edge.target_type : edge.source_type
    const targetId   = edge.direction === 'out'
      ? (edge.target_id || edge.target_type)
      : (edge.source_id || edge.source_type)
    if (!targetType || !targetId) return

    if (selectedNode) {
      setNavHistory(prev => [...prev.slice(-4), { type: selectedType, node: selectedNode }])
    }

    setSelectedType(targetType)
    setSearch('')
    const data = await getNodesByType(targetType, 100)
    const newNodes: NodeProps[] = data.nodes || []
    setNodes(newNodes)
    setLoadingNodes(false)

    const match = newNodes.find(n =>
      String(n.id || n.name || n.type || n.level || '') === String(targetId)
    )
    if (match) {
      setSelectedNode(match)
      updateUrl(targetType, String(targetId))
      const allGroups = new Set(newNodes.map(n => getGroupKey(n)).filter(Boolean) as string[])
      const matchGroup = getGroupKey(match)
      if (matchGroup) allGroups.delete(matchGroup)
      setCollapsedGroups(allGroups)
    } else {
      updateUrl(targetType)
      const allGroups = new Set(newNodes.map(n => getGroupKey(n)).filter(Boolean) as string[])
      setCollapsedGroups(allGroups)
    }
  }, [selectedNode, selectedType, updateUrl])

  // Load schema on mount
  useEffect(() => {
    getGraphSchema().then(d => {
      setSchema(d.schema || [])
      setLoading(false)
    })
  }, [])

  // Load nodes when type changes
  useEffect(() => {
    if (!selectedType) return
    setLoadingNodes(true)
    setSelectedNode(null)
    setSearch('')
    getNodesByType(selectedType, 100).then(d => {
      const newNodes = d.nodes || []
      setNodesError(!!d.error)
      setNodes(newNodes)
      // Collapse all groups by default
      const allGroups = new Set(newNodes.map((n: NodeProps) => getGroupKey(n)).filter(Boolean) as string[])
      setCollapsedGroups(allGroups)
      // Auto-select node from URL ?node= param
      if (urlNode) {
        const match = newNodes.find((n: NodeProps) =>
          String(n.id || n.name || n.type || n.level || '').toLowerCase() === urlNode.toLowerCase()
        )
        if (match) {
          setSelectedNode(match)
          // Expand that node's group
          const matchGroup = getGroupKey(match)
          if (matchGroup) {
            setCollapsedGroups(prev => {
              const next = new Set(prev)
              next.delete(matchGroup)
              return next
            })
          }
        }
      }
      setLoadingNodes(false)
    })
  }, [selectedType, urlNode])

  // Load edges when node selected
  useEffect(() => {
    if (!selectedNode) return
    setLoadingEdges(true)
    setTextExpanded(false)
    setShowRaw(false)
    const nodeId = getNodeDisplayId(selectedNode)
    getNodeEdges(selectedType, nodeId).then(d => {
      setEdges(d.edges || [])
      setLoadingEdges(false)
    })
  }, [selectedNode, selectedType])

  // Load ego graph when visualizer is toggled on
  useEffect(() => {
    if (!showGraph || !selectedNode) return
    setLoadingGraph(true)
    const nodeId = getNodeDisplayId(selectedNode)
    getEgoGraph(selectedType, nodeId).then(d => {
      setEgoGraph(d)
      setLoadingGraph(false)
    })
  }, [showGraph, selectedNode, selectedType])

  const filteredNodes = nodes.filter(n => {
    if (!search) return true
    const id = getNodeDisplayId(n).toLowerCase()
    const title = getNodeDisplayTitle(n).toLowerCase()
    return id.includes(search.toLowerCase()) || title.includes(search.toLowerCase())
  })

  const grouped = filteredNodes.reduce((acc, node) => {
    const key = getGroupKey(node)
    if (!acc[key]) acc[key] = []
    acc[key].push(node)
    return acc
  }, {} as Record<string, NodeProps[]>)

  const isGrouped = Object.keys(grouped).length > 1 &&
    Object.keys(grouped).every(k => k !== '')

  const SKIP_PROPS = new Set(['text', 'title_de', 'title_en', 'id', 'name', 'type', 'description', 'note', 'copyright_cleared', 'level'])

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)', display: 'flex' }}>
      <Sidebar />

      {/* Main content area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, minHeight: '100vh' }}>

        {/* Schema header */}
        <div style={{
          padding: '12px 24px',
          borderBottom: '1px solid var(--border-default)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'var(--bg-surface)',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <span style={{
              fontSize: '13px',
              color: 'var(--text-primary)',
              fontWeight: 500,
            }}>
              Compliance Brain
            </span>
            <span style={{
              fontSize: '11px',
              color: 'var(--text-muted)',
              fontFamily: 'ui-monospace, monospace',
            }}>
              {schema.reduce((s, e) => s + e.count, 0)} nodes · deterministic graph · not AI-generated
            </span>
            <span style={{
              fontSize: '10px',
              color: 'var(--text-muted)',
              opacity: 0.75,
              fontFamily: 'ui-monospace, monospace',
            }}>
              regulatory content seeded from verified official sources · every node carries its source
            </span>
          </div>
          <span style={{
            fontSize: '10px',
            color: 'var(--text-muted)',
            fontFamily: 'ui-monospace, monospace',
            letterSpacing: '0.06em',
          }}>
            Click any node to inspect · edges are clickable
          </span>
        </div>

        {/* Three-column layout */}
        <div style={{ flex: 1, display: 'flex', minWidth: 0 }}>

        {/* Column 1: Node Types */}
        <div style={{
          width: '220px',
          flexShrink: 0,
          background: 'var(--bg-surface)',
          borderRight: '1px solid var(--border-default)',
          display: 'flex',
          flexDirection: 'column',
          overflowY: 'auto',
        }}>
          <div style={{
            padding: '16px 16px 8px',
            fontSize: '10px',
            fontWeight: 600,
            color: 'var(--text-muted)',
            letterSpacing: '0.08em',
            fontFamily: 'ui-monospace, monospace',
          }}>
            NODE REGISTRY
          </div>
          {loading ? (
            <div style={{ padding: '16px', fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'ui-monospace, monospace' }}>
              Loading...
            </div>
          ) : (
            schema.map(entry => {
              const active = entry.label === selectedType
              const meta = NODE_TYPE_META[entry.label] || { icon: '◯', description: '' }
              return (
                <div
                  key={entry.label}
                  onClick={() => { setSelectedType(entry.label); updateUrl(entry.label) }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '9px 16px',
                    cursor: 'pointer',
                    background: active ? 'rgba(74,143,255,0.08)' : 'transparent',
                    borderLeft: active ? '2px solid var(--accent)' : '2px solid transparent',
                    transition: 'all 150ms ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                    <span style={{ fontSize: '12px', color: active ? 'var(--accent)' : 'var(--text-muted)', opacity: 0.8, flexShrink: 0 }}>
                      {meta.icon}
                    </span>
                    <div style={{ minWidth: 0 }}>
                      <span style={{ fontSize: '13px', color: active ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                        {entry.label}
                      </span>
                      {meta.description && (
                        <div style={{
                          fontSize: '10px', color: 'var(--text-muted)', opacity: 0.65,
                          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                        }} title={meta.description}>
                          {meta.description}
                        </div>
                      )}
                    </div>
                  </div>
                  <span style={{
                    fontSize: '11px',
                    color: 'var(--text-muted)',
                    fontFamily: 'ui-monospace, monospace',
                  }}>
                    {entry.count}
                  </span>
                </div>
              )
            })
          )}
        </div>

        {/* Column 2: Node List */}
        <div style={{
          width: '280px',
          flexShrink: 0,
          borderRight: '1px solid var(--border-default)',
          display: 'flex',
          flexDirection: 'column',
          overflowY: 'auto',
        }}>
          {/* Search */}
          <div style={{ padding: '12px', borderBottom: '1px solid var(--border-default)' }}>
            <input
              type="text"
              placeholder={`Search ${selectedType}...`}
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{
                width: '100%',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-default)',
                borderRadius: '4px',
                padding: '6px 10px',
                fontSize: '12px',
                color: 'var(--text-primary)',
                fontFamily: 'ui-monospace, monospace',
                outline: 'none',
              }}
            />
          </div>

          {/* Count */}
          <div style={{
            padding: '8px 12px',
            fontSize: '10px',
            color: 'var(--text-muted)',
            fontFamily: 'ui-monospace, monospace',
            borderBottom: '1px solid var(--border-default)',
          }}>
            {filteredNodes.length} nodes
          </div>

          {/* Node list */}
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {loadingNodes ? (
              <div style={{ padding: '16px', fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'ui-monospace, monospace' }}>
                Loading...
              </div>
            ) : isGrouped ? (
              sortGroups(grouped, selectedType).map(([groupKey, groupNodes]) => {
                const isCollapsed = collapsedGroups.has(groupKey)
                return (
                  <div key={groupKey}>
                    <div
                      onClick={() => setCollapsedGroups(prev => {
                        const next = new Set(prev)
                        if (next.has(groupKey)) next.delete(groupKey)
                        else next.add(groupKey)
                        return next
                      })}
                      style={{
                        padding: '8px 12px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        cursor: 'pointer',
                        background: 'var(--bg-elevated)',
                        borderBottom: '1px solid var(--border-default)',
                        position: 'sticky',
                        top: 0,
                      }}
                    >
                      <span style={{
                        fontSize: '11px',
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                        fontFamily: 'ui-monospace, monospace',
                        letterSpacing: '0.04em',
                      }}>
                        {groupKey}
                      </span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'ui-monospace, monospace' }}>
                          {groupNodes.length}
                        </span>
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                          {isCollapsed ? '▶' : '▼'}
                        </span>
                      </span>
                    </div>
                    {!isCollapsed && (groupNodes as NodeProps[]).map((node: NodeProps, i: number) => {
                      const nodeId = getNodeDisplayId(node)
                      const title = getNodeDisplayTitle(node)
                      const isSelected = selectedNode === node
                      return (
                        <div
                          key={i}
                          onClick={() => { setSelectedNode(node); updateUrl(selectedType, nodeId) }}
                          style={{
                            padding: '8px 12px 8px 20px',
                            cursor: 'pointer',
                            background: isSelected ? 'rgba(74,143,255,0.08)' : 'transparent',
                            borderLeft: isSelected ? '2px solid var(--accent)' : '2px solid transparent',
                            borderBottom: '1px solid rgba(255,255,255,0.04)',
                            transition: 'all 100ms ease',
                          }}
                          onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'var(--bg-elevated)' }}
                          onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent' }}
                        >
                          <div style={{
                            fontSize: '11px',
                            fontFamily: 'ui-monospace, monospace',
                            color: isSelected ? 'var(--accent)' : 'var(--text-secondary)',
                          }}>
                            {node.article ? `Art. ${node.article}` : nodeId}
                          </div>
                          {title && (
                            <div style={{
                              fontSize: '11px',
                              color: 'var(--text-muted)',
                              marginTop: '1px',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}>
                              {title}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )
              })
            ) : (
              filteredNodes.map((node, i) => {
                const nodeId = getNodeDisplayId(node)
                const title = getNodeDisplayTitle(node)
                const isSelected = selectedNode === node
                return (
                  <div
                    key={i}
                    onClick={() => { setSelectedNode(node); updateUrl(selectedType, nodeId) }}
                    style={{
                      padding: '10px 12px',
                      cursor: 'pointer',
                      background: isSelected ? 'rgba(74,143,255,0.08)' : 'transparent',
                      borderLeft: isSelected ? '2px solid var(--accent)' : '2px solid transparent',
                      borderBottom: '1px solid rgba(255,255,255,0.04)',
                      transition: 'all 100ms ease',
                    }}
                    onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'var(--bg-elevated)' }}
                    onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent' }}
                  >
                    <div style={{
                      fontSize: '12px',
                      fontFamily: 'ui-monospace, monospace',
                      color: isSelected ? 'var(--accent)' : 'var(--text-primary)',
                      fontWeight: 500,
                    }}>
                      {nodeId}
                    </div>
                    {title && (
                      <div style={{
                        fontSize: '11px',
                        color: 'var(--text-muted)',
                        marginTop: '2px',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}>
                        {title}
                      </div>
                    )}
                  </div>
                )
              })
            )}
          </div>
        </div>

        {/* Column 3: Inspector */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px 32px' }}>
          {!selectedNode ? (
            <div style={{
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexDirection: 'column',
              gap: '8px',
            }}>
              <div style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
                Select a node to inspect
              </div>
              <div style={{ fontSize: '12px', color: nodesError ? '#f87171' : 'var(--text-muted)', fontFamily: 'ui-monospace, monospace' }}>
                {nodesError
                  ? `${selectedType} · node list unavailable — API error (backend rejected the type)`
                  : `${selectedType} · ${nodes.length} nodes loaded`}
              </div>
            </div>
          ) : (
            <>
              {/* Breadcrumb navigation */}
              {navHistory.length > 0 && (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  marginBottom: '16px',
                  flexWrap: 'wrap',
                }}>
                  {navHistory.map((h, i) => {
                    const label = h.node.short || (h.node.article ? `Art. ${h.node.article}` : null)
                      || String(h.node.id || h.node.name || h.node.type || '—')
                    return (
                      <span key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                          [{h.type}]
                        </span>
                        <span
                          onClick={() => {
                            setSelectedType(h.type)
                            setSelectedNode(h.node)
                            setNavHistory(prev => prev.slice(0, i))
                          }}
                          style={{
                            fontSize: '11px',
                            color: 'var(--accent)',
                            fontFamily: 'ui-monospace, monospace',
                            cursor: 'pointer',
                            textDecoration: 'underline',
                            textDecorationColor: 'rgba(74,143,255,0.3)',
                          }}
                        >
                          {label}
                        </span>
                        <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>→</span>
                      </span>
                    )
                  })}
                </div>
              )}

              {/* Node header */}
              <div style={{ marginBottom: '24px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <div style={{
                    fontSize: '24px',
                    fontWeight: 700,
                    color: 'var(--text-primary)',
                    fontFamily: 'ui-monospace, monospace',
                    letterSpacing: '-0.02em',
                  }}>
                    {getNodeDisplayId(selectedNode)}
                  </div>
                  <button
                    onClick={() => setShowGraph(!showGraph)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '4px 12px',
                      background: showGraph ? 'rgba(74,143,255,0.15)' : 'transparent',
                      border: `1px solid ${showGraph ? 'var(--accent)' : 'var(--border-default)'}`,
                      borderRadius: '4px',
                      fontSize: '11px',
                      color: showGraph ? 'var(--accent)' : 'var(--text-muted)',
                      cursor: 'pointer',
                      fontFamily: 'ui-monospace, monospace',
                      transition: 'all 150ms ease',
                      flexShrink: 0,
                    }}
                  >
                    {showGraph ? 'Inspector' : 'Visualize'}
                  </button>
                </div>
                {/* title_en — primary (EN default per ADR-047) */}
                {selectedNode.title_en && (
                  <div style={{ fontSize: '16px', color: 'var(--text-secondary)', marginBottom: '2px' }}>
                    {selectedNode.title_en as string}
                  </div>
                )}
                {/* title_de — subtitle if different from EN */}
                {selectedNode.title_de && selectedNode.title_de !== selectedNode.title_en && (
                  <div style={{ fontSize: '13px', color: 'var(--text-muted)', fontFamily: 'ui-monospace, monospace' }}>
                    {selectedNode.title_de as string}
                  </div>
                )}
              </div>

              {/* Graph Visualizer */}
              {showGraph && (
                <div style={{ marginBottom: '16px' }}>
                  {loadingGraph ? (
                    <div style={{
                      minHeight: '400px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: '#080b12',
                      borderRadius: '6px',
                      border: '1px solid var(--border-default)',
                    }}>
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'ui-monospace, monospace' }}>
                        Loading graph...
                      </span>
                    </div>
                  ) : egoGraph && egoGraph.nodes.length > 0 ? (
                    <EgoGraph
                      nodes={egoGraph.nodes}
                      edges={egoGraph.edges}
                      centerId={egoGraph.center_id}
                      onNodeClick={(node) => {
                        if (selectedNode) {
                          setNavHistory(prev => [...prev.slice(-4), { type: selectedType, node: selectedNode }])
                        }
                        setSelectedType(node.type)
                        setShowGraph(false)
                        setSearch('')
                        setCollapsedGroups(new Set())
                        getNodesByType(node.type, 100).then(d => {
                          const newNodes = d.nodes || []
                          setNodes(newNodes)
                          const match = newNodes.find((n: NodeProps) =>
                            String(n.id || n.name || n.type || '') === String(node.id)
                          )
                          if (match) setSelectedNode(match)
                        })
                      }}
                    />
                  ) : (
                    <div style={{
                      minHeight: '200px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: '#080b12',
                      borderRadius: '6px',
                      border: '1px solid var(--border-default)',
                    }}>
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'ui-monospace, monospace' }}>
                        No graph data available
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* Copyright status badge — only when explicitly set */}
              {!showGraph && selectedNode.copyright_cleared !== undefined && selectedNode.copyright_cleared !== null && (
                <div style={{ marginBottom: '14px' }}>
                  <span style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '5px',
                    padding: '3px 10px',
                    borderRadius: '10px',
                    fontSize: '10px',
                    fontFamily: 'ui-monospace, monospace',
                    fontWeight: 600,
                    ...(selectedNode.copyright_cleared
                      ? {
                          background: 'rgba(74,222,128,0.10)',
                          color: 'var(--state-pass)',
                          border: '1px solid rgba(74,222,128,0.2)',
                        }
                      : {
                          background: 'rgba(245,158,11,0.10)',
                          color: 'var(--state-warn)',
                          border: '1px solid rgba(245,158,11,0.2)',
                        }
                    ),
                  }}>
                    {selectedNode.copyright_cleared
                      ? '\u2713 Public domain \u2014 amtliches Werk \u00a7 5 UrhG'
                      : '\u26a0 Not cleared for commercial use'}
                  </span>
                </div>
              )}

              {/* Compact confidence + severity bar */}
              {!showGraph && selectedNode.confidence !== undefined && (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  marginBottom: '16px',
                  padding: '10px 14px',
                  background: 'var(--bg-surface)',
                  borderRadius: '5px',
                  border: '1px solid var(--border-default)',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'ui-monospace, monospace' }}>
                      Confidence
                    </span>
                    <div style={{ width: '80px', height: '3px', background: 'var(--border-default)', borderRadius: '2px' }}>
                      <div style={{
                        width: `${Math.round((selectedNode.confidence as number) * 100)}%`,
                        height: '100%',
                        background: 'var(--state-pass)',
                        borderRadius: '2px',
                      }} />
                    </div>
                    <span style={{ fontSize: '11px', color: 'var(--state-pass)', fontFamily: 'ui-monospace, monospace' }}>
                      {selectedNode.confidence as number} — primary source
                    </span>
                  </div>
                  {selectedNode.severity && (
                    <SeverityBadge value={selectedNode.severity as string} />
                  )}
                  {selectedNode.source && (
                    <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'ui-monospace, monospace' }}>Source</span>
                      <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'ui-monospace, monospace', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {selectedNode.source as string}
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* WHY THIS MATTERS — context card */}
              {!showGraph && !loadingEdges && (() => {
                const ctx = buildContextSummary(selectedType, selectedNode, edges)
                return ctx ? <ContextCard text={ctx} /> : null
              })()}

              {/* WHAT THIS NODE TRIGGERS — outgoing edges */}
              {!showGraph && !loadingEdges && (() => {
                const outEdges = edges.filter(e => e.direction === 'out')
                const outByRel = outEdges.reduce((acc, e) => {
                  const key = `${e.rel}__${e.target_type}`
                  if (!acc[key]) acc[key] = { rel: e.rel, targetType: e.target_type || '', edges: [] }
                  acc[key].edges.push(e)
                  return acc
                }, {} as Record<string, { rel: string; targetType: string; edges: typeof edges }>)
                const groups = Object.values(outByRel)

                if (groups.length === 0) return null
                return (
                  <div style={{ marginBottom: '16px' }}>
                    <div style={{
                      fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)',
                      letterSpacing: '0.08em', fontFamily: 'ui-monospace, monospace',
                      marginBottom: '8px',
                    }}>
                      WHAT THIS NODE TRIGGERS
                    </div>
                    {groups.map(g => (
                      <EdgeGroup
                        key={`out-${g.rel}-${g.targetType}`}
                        direction="out"
                        rel={g.rel}
                        targetType={g.targetType}
                        edgeNodes={g.edges}
                        explanation={EDGE_EXPLANATIONS[g.rel]?.out || g.rel}
                        onNodeClick={handleEdgeClick}
                      />
                    ))}
                  </div>
                )
              })()}

              {/* WHAT REFERENCES THIS NODE — incoming edges */}
              {!showGraph && !loadingEdges && (() => {
                const inEdges = edges.filter(e => e.direction === 'in')
                const inByRel = inEdges.reduce((acc, e) => {
                  const key = `${e.rel}__${e.source_type}`
                  if (!acc[key]) acc[key] = { rel: e.rel, sourceType: e.source_type || '', edges: [] }
                  acc[key].edges.push(e)
                  return acc
                }, {} as Record<string, { rel: string; sourceType: string; edges: typeof edges }>)
                const groups = Object.values(inByRel)

                if (groups.length === 0) return null
                return (
                  <div style={{ marginBottom: '16px' }}>
                    <div style={{
                      fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)',
                      letterSpacing: '0.08em', fontFamily: 'ui-monospace, monospace',
                      marginBottom: '8px',
                    }}>
                      WHAT REFERENCES THIS NODE ({inEdges.length})
                    </div>
                    {groups.map(g => (
                      <EdgeGroup
                        key={`in-${g.rel}-${g.sourceType}`}
                        direction="in"
                        rel={g.rel}
                        targetType={g.sourceType}
                        edgeNodes={g.edges}
                        explanation={EDGE_EXPLANATIONS[g.rel]?.in || g.rel}
                        onNodeClick={handleEdgeClick}
                      />
                    ))}
                  </div>
                )
              })()}

              {/* Loading edges indicator */}
              {!showGraph && loadingEdges && (
                <div style={{ padding: '8px 0', fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'ui-monospace, monospace' }}>
                  Loading edges...
                </div>
              )}

              {/* Norm text — collapsible */}
              {!showGraph && selectedNode.text && (
                <div style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-default)',
                  borderRadius: '6px',
                  overflow: 'hidden',
                  marginBottom: '16px',
                }}>
                  <div
                    style={{
                      padding: '8px 14px',
                      borderBottom: textExpanded ? '1px solid var(--border-default)' : 'none',
                      fontSize: '10px',
                      fontWeight: 600,
                      color: 'var(--text-muted)',
                      letterSpacing: '0.08em',
                      fontFamily: 'ui-monospace, monospace',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      cursor: 'pointer',
                    }}
                    onClick={() => setTextExpanded(!textExpanded)}
                  >
                    <span>NORM TEXT</span>
                    <span style={{ color: 'var(--accent)' }}>{textExpanded ? '▲' : '▼'}</span>
                  </div>
                  {textExpanded && (
                    <div style={{
                      padding: '12px 14px',
                      fontSize: '12px',
                      color: 'var(--text-secondary)',
                      fontFamily: 'ui-monospace, monospace',
                      lineHeight: '1.6',
                      maxHeight: '300px',
                      overflowY: 'auto',
                    }}>
                      {selectedNode.text as string}
                    </div>
                  )}
                </div>
              )}

              {/* Raw graph properties — collapsed by default */}
              {!showGraph && (
                <div style={{ marginTop: '8px' }}>
                  <div
                    onClick={() => setShowRaw(!showRaw)}
                    style={{
                      fontSize: '11px',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      padding: '8px 0',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      fontFamily: 'ui-monospace, monospace',
                    }}
                  >
                    <span>{showRaw ? '▼' : '▸'}</span>
                    {showRaw ? 'Hide raw properties' : 'Show raw graph properties'}
                  </div>

                  {showRaw && (
                    <div style={{
                      background: 'var(--bg-surface)',
                      border: '1px solid var(--border-default)',
                      borderRadius: '4px',
                      padding: '10px 12px',
                    }}>
                      {Object.entries(selectedNode)
                        .filter(([k]) => !SKIP_PROPS.has(k))
                        .map(([key, value]) => (
                          <div key={key} style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            gap: '16px',
                            padding: '3px 0',
                            borderBottom: '1px solid rgba(255,255,255,0.03)',
                          }}>
                            <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'ui-monospace, monospace', flexShrink: 0 }}>
                              {PROP_LABELS[key] || key}
                            </span>
                            <span style={{ fontSize: '10px', color: 'rgba(100,116,139,0.7)', textAlign: 'right', wordBreak: 'break-all', fontFamily: 'ui-monospace, monospace' }}>
                              {Array.isArray(value) ? value.join(', ') : String(value)}
                            </span>
                          </div>
                        ))
                      }
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
      </div>
    </div>
  )
}

export default function SchemaPage() {
  return (
    <Suspense fallback={
      <div style={{ minHeight: '100vh', background: 'var(--bg-base)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'ui-monospace, monospace' }}>Loading...</span>
      </div>
    }>
      <SchemaPageInner />
    </Suspense>
  )
}
