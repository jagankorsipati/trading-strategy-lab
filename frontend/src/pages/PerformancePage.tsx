import { useEffect, useMemo, useState } from 'react'
import { useApi } from '../api/useApi'
import { LineSeriesChart, ScenarioBarChart } from '../charts/ResearchCharts'
import { EmptyState, ErrorState, LoadingState, PageHeader, Panel } from '../components/ui'
import type { Run, Series, Trade } from '../types'

export function PerformancePage() {
  const runs = useApi<{ items: Run[] }>('/runs?run_type=standard_backtest&page_size=100')
  const [runId, setRunId] = useState('')
  useEffect(() => { if (!runId && runs.data?.items.length) setRunId(runs.data.items[0].id) }, [runs.data, runId])
  const equity = useApi<Series>(runId ? `/runs/${runId}/equity` : null)
  const drawdown = useApi<Series>(runId ? `/runs/${runId}/drawdown` : null)
  const monthly = useApi<Series>(runId ? `/runs/${runId}/monthly` : null)
  const trades = useApi<{ items: Trade[] }>(runId ? `/runs/${runId}/trades?page_size=250` : null)
  const exitData = useMemo(() => {
    const counts: Record<string, number> = {}
    trades.data?.items.forEach(item => { counts[item.exit_reason] = (counts[item.exit_reason] ?? 0) + 1 })
    return Object.entries(counts).map(([scenario, value]) => ({ scenario, returnValue: value }))
  }, [trades.data])
  if (runs.loading) return <LoadingState/>
  if (runs.error) return <ErrorState message={runs.error}/>
  if (!runs.data?.items.length) return <EmptyState label="No trade-level runs support performance charts."/>
  return <><PageHeader eyebrow="Risk and path" title="Performance dashboard">Axes, units, source period, and realized-only limitations are shown explicitly.</PageHeader><Panel className="filters"><label>Run<select value={runId} onChange={e => setRunId(e.target.value)}>{runs.data.items.map(run => <option value={run.id} key={run.id}>{run.strategy} · {run.start_date} to {run.end_date}</option>)}</select></label><div className="filter-note">Fixed 0 bps · recorded artifact</div></Panel><div className="chart-grid"><Panel><h2>Realized equity</h2>{equity.loading ? <LoadingState/> : equity.error ? <ErrorState message={equity.error}/> : <><LineSeriesChart data={equity.data?.points ?? []} unit="USD" label="Realized equity in US dollars"/><p className="method">{equity.data?.methodology}</p></>}</Panel><Panel><h2>Drawdown</h2>{drawdown.loading ? <LoadingState/> : <><LineSeriesChart data={drawdown.data?.points ?? []} unit="percent" label="Realized equity drawdown percentage"/><p className="method">{drawdown.data?.methodology}</p></>}</Panel><Panel><h2>Monthly realized P&L</h2><ScenarioBarChart data={(monthly.data?.points ?? []).map(p => ({ scenario: p.timestamp.slice(0,7), returnValue: p.value }))} label="Monthly realized profit and loss in dollars"/></Panel><Panel><h2>Exit-reason distribution</h2><ScenarioBarChart data={exitData} label="Trade count by exit reason"/><p className="method">Counts, not percentages. Color includes text labels and tooltips.</p></Panel></div></>
}
