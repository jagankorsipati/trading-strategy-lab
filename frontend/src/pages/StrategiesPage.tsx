import { ExternalLink, LockKeyhole } from 'lucide-react'
import { RouterLink as Link } from '../components/Router'
import { useApi } from '../api/useApi'
import { Badge, EmptyState, ErrorState, LoadingState, PageHeader, Panel } from '../components/ui'
import type { Strategy } from '../types'
import { money, percent } from '../utils/format'

export function StrategiesPage() {
  const { data, loading, error } = useApi<Strategy[]>('/strategies')
  if (loading) return <LoadingState/>
  if (error) return <ErrorState message={error}/>
  if (!data?.length) return <EmptyState/>
  return <><PageHeader eyebrow="Immutable references" title="Strategy catalog">Baseline metadata and assumptions are read-only. New research must use a new strategy version.</PageHeader><div className="strategy-grid">{data.map(strategy => <Panel key={strategy.id} className="strategy-card"><div className="card-top"><Badge tone="warning"><LockKeyhole size={13}/> {strategy.status}</Badge><span className="mono">{strategy.baseline_release}</span></div><h2>{strategy.name}</h2><p>{strategy.sizing}</p><dl className="definition-list"><div><dt>Starting capital</dt><dd>{money(strategy.starting_capital)}</dd></div>{Object.entries(strategy.default_assumptions).map(([key,value]) => <div key={key}><dt>{key.replaceAll('_',' ')}</dt><dd>{String(value)}</dd></div>)}</dl><div className="friction-strip"><div><span>0 bps</span><strong>{percent(strategy.key_results.zero_bps_return)}</strong></div><div><span>2 bps</span><strong>{percent(strategy.key_results.two_bps_return)}</strong></div><div><span>5 bps</span><strong>{percent(strategy.key_results.five_bps_return)}</strong></div></div><div className="conclusion"><strong>Research conclusion</strong><p>{strategy.conclusion}</p></div><Link className="text-link" to="/reports">Open specification <ExternalLink size={14}/></Link></Panel>)}</div></>
}
