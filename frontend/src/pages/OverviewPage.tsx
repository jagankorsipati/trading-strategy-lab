import { ArrowRight, LockKeyhole } from 'lucide-react'
import { RouterLink as Link } from '../components/Router'
import { useApi } from '../api/useApi'
import { ArtifactCount, Badge, EmptyState, ErrorState, LoadingState, MetricCard, PageHeader, Panel } from '../components/ui'
import type { Run, Strategy, Study } from '../types'
import { percent } from '../utils/format'

export function OverviewPage() {
  const strategies = useApi<Strategy[]>('/strategies')
  const runs = useApi<{ items: Run[]; total: number }>('/runs?page_size=100')
  const walks = useApi<Study[]>('/walk-forward')
  const executions = useApi<Study[]>('/execution-studies')
  if ([strategies, runs, walks, executions].some(item => item.loading)) return <LoadingState label="Cataloging research evidence..."/>
  const error = [strategies, runs, walks, executions].find(item => item.error)?.error
  if (error) return <ErrorState message={error}/>
  if (!strategies.data?.length) return <EmptyState label="No strategy metadata is available."/>
  const fixed2 = runs.data?.items.filter(run => run.execution_model === 'fixed-2bps') ?? []
  return <>
    <PageHeader eyebrow="Evidence first" title="Research, without the sales pitch">A transparent view of frozen strategies, historical results, execution assumptions, and the source artifacts behind every number.</PageHeader>
    <div className="hero-grid"><Panel className="hero-panel"><Badge tone="warning"><LockKeyhole size={13}/> Baselines frozen</Badge><h2>Gross edge observed.<br/>Friction-resistant edge not established.</h2><p>Both baselines produce positive zero-friction histories, then lose under 2 bps adverse slippage. Rolling out-of-sample evidence is not sufficient for strategy-driven paper trading.</p><Link className="text-link" to="/comparison">Inspect the comparison <ArrowRight size={15}/></Link></Panel>
      <div className="metric-grid compact"><MetricCard label="Project version" value="0.1.0" context="Research foundation"/><MetricCard label="Test metadata" value="Unavailable" context="Run verification locally"/><MetricCard label="Frozen strategies" value={String(strategies.data.length)} context="No UI parameter editing"/><MetricCard label="2 bps survivors" value={`${fixed2.filter(run => run.profitable).length}/${fixed2.length || 2}`} context="Continuous 2018-2025"/></div>
    </div>
    <div className="section-title"><div><p className="eyebrow">Artifact inventory</p><h2>Available evidence</h2></div></div>
    <div className="artifact-grid"><ArtifactCount label="Strategies" value={strategies.data.length}/><ArtifactCount label="Research runs" value={runs.data?.total ?? 0}/><ArtifactCount label="Walk-forward studies" value={walks.data?.length ?? 0}/><ArtifactCount label="Execution studies" value={executions.data?.length ?? 0}/></div>
    <Panel><div className="section-title"><div><p className="eyebrow">Frozen comparison</p><h2>Continuous execution sensitivity</h2></div><span className="unit-label">2018-2025 | total return</span></div><div className="comparison-rows">{strategies.data.map(strategy => <div className="comparison-row" key={strategy.id}><div><strong>{strategy.name}</strong><span>{strategy.sizing}</span></div><div><small>0 bps</small><b>{percent(strategy.key_results.zero_bps_return)}</b></div><div><small>2 bps</small><b>{percent(strategy.key_results.two_bps_return)}</b></div><div><small>5 bps</small><b>{percent(strategy.key_results.five_bps_return)}</b></div></div>)}</div></Panel>
  </>
}
