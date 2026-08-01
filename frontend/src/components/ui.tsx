import type { ReactNode } from 'react'
import { AlertTriangle, Database, FileSearch, LockKeyhole } from 'lucide-react'
import type { Provenance } from '../types'

export function ResearchNotice() {
  return <div className="notice" role="note"><AlertTriangle size={18}/><div><strong>Research and educational use only.</strong><span>Historical performance does not guarantee future results. No current baseline strategy demonstrates a friction-resistant edge.</span></div></div>
}
export function LoadingState({ label = 'Loading research artifacts…' }: { label?: string }) { return <div className="state"><div className="spinner"/><p>{label}</p></div> }
export function EmptyState({ label = 'No matching artifacts are available.' }: { label?: string }) { return <div className="state"><FileSearch/><p>{label}</p></div> }
export function ErrorState({ message }: { message: string }) { return <div className="state error"><AlertTriangle/><p>{message}</p></div> }
export function Panel({ children, className = '' }: { children: ReactNode; className?: string }) { return <section className={`panel ${className}`}>{children}</section> }
export function PageHeader({ eyebrow, title, children }: { eyebrow: string; title: string; children?: ReactNode }) { return <header className="page-header"><p className="eyebrow">{eyebrow}</p><h1>{title}</h1>{children && <p>{children}</p>}</header> }
export function MetricCard({ label, value, context }: { label: string; value: string; context?: string }) { return <div className="metric-card"><span>{label}</span><strong>{value}</strong>{context && <small>{context}</small>}</div> }
export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral'|'warning'|'info' }) { return <span className={`badge ${tone}`}>{children}</span> }
export function ProvenancePanel({ provenance }: { provenance: Provenance }) {
  const values = [
    ['Source', provenance.source_file], ['Strategy', provenance.strategy_version],
    ['Baseline', provenance.baseline_status], ['Period', provenance.data_period],
    ['Execution', provenance.execution_model], ['Slippage', provenance.slippage_bps == null ? null : `${provenance.slippage_bps} bps`],
    ['Generated', provenance.generated_time], ['Project', provenance.project_version], ['Commit', provenance.commit_hash],
  ]
  return <Panel><div className="section-title"><div><p className="eyebrow">Traceability</p><h2>Provenance</h2></div><LockKeyhole size={18}/></div><dl className="provenance">{values.map(([k,v]) => <div key={k}><dt>{k}</dt><dd>{v ?? 'Unavailable'}</dd></div>)}</dl></Panel>
}
export function ArtifactCount({ label, value }: { label: string; value: number }) { return <div className="artifact-count"><Database size={16}/><span>{label}</span><strong>{value}</strong></div> }
