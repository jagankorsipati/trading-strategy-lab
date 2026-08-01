import { useApi } from '../api/useApi'
import { ScenarioBarChart } from '../charts/ResearchCharts'
import { ErrorState, LoadingState, PageHeader, Panel } from '../components/ui'
import type { Run } from '../types'
import { money, percent } from '../utils/format'

export function ComparisonPage() {
  const runs = useApi<{ items: Run[] }>('/runs?run_type=execution_study&page_size=100')
  if (runs.loading) return <LoadingState/>
  if (runs.error) return <ErrorState message={runs.error}/>
  const fixed = runs.data?.items.filter(run => ['fixed-0bps','fixed-2bps','fixed-5bps'].includes(run.execution_model ?? '')) ?? []
  return <><PageHeader eyebrow="Normalized comparison" title="Strategy comparison">Percentage and risk metrics are primary because the frozen strategies use different starting capital.</PageHeader><Panel><div className="section-title"><div><p className="eyebrow">Friction sensitivity</p><h2>Total return by baseline and model</h2></div><span className="unit-label">Percent return · not dollar P&L</span></div><ScenarioBarChart data={fixed.map(run => ({ scenario: `${run.strategy}\n${run.execution_model}`, returnValue: run.total_return ?? 0 }))}/></Panel><div className="comparison-grid">{['orb-v1','reference-orb-v1'].map(strategy => <Panel key={strategy}><h2>{strategy}</h2><div className="comparison-rows">{fixed.filter(run => run.strategy===strategy).map(run => <div className="mini-row" key={run.id}><span>{run.execution_model}</span><strong>{percent(run.total_return)}</strong><small>Start {money(run.starting_equity)}</small></div>)}</div></Panel>)}</div><Panel className="comparison-warning"><h2>Comparison guardrail</h2><p>Dollar P&L is intentionally not used as the lead comparison: ORB-v1 starts at $10,000 while Reference-ORB-v1 starts at $25,000. Exposure, sizing, targets, and commissions also differ.</p></Panel></>
}
