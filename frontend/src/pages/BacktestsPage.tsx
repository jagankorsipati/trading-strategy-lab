import { useEffect, useState } from 'react'
import { useApi } from '../api/useApi'
import { EmptyState, ErrorState, LoadingState, MetricCard, PageHeader, Panel, ProvenancePanel } from '../components/ui'
import type { Metrics, Run } from '../types'
import { money, number, percent } from '../utils/format'

export function BacktestsPage() {
  const runs = useApi<{ items: Run[]; total: number }>('/runs?page_size=100')
  const [selected, setSelected] = useState('')
  useEffect(() => { if (!selected && runs.data?.items.length) setSelected(runs.data.items[0].id) }, [runs.data, selected])
  const metrics = useApi<Metrics>(selected ? `/runs/${selected}/metrics` : null)
  if (runs.loading) return <LoadingState/>
  if (runs.error) return <ErrorState message={runs.error}/>
  if (!runs.data?.items.length) return <EmptyState label="No backtest runs were discovered."/>
  const run = runs.data.items.find(item => item.id === selected) ?? runs.data.items[0]
  const m = metrics.data?.metrics ?? {}
  return <><PageHeader eyebrow="Artifact browser" title="Backtest explorer">Filter recorded runs and inspect their assumptions. This interface cannot initiate or modify a backtest.</PageHeader><Panel className="filters"><label>Run<select value={selected} onChange={event => setSelected(event.target.value)}>{runs.data.items.map(item => <option key={item.id} value={item.id}>{item.strategy} · {item.execution_model} · {item.run_type}</option>)}</select></label><label>Strategy<input value={run.strategy} readOnly/></label><label>Period<input value={`${run.start_date ?? 'Unavailable'} — ${run.end_date ?? 'Unavailable'}`} readOnly/></label><label>Execution<input value={run.execution_model ?? 'Unavailable'} readOnly/></label></Panel>{metrics.loading ? <LoadingState label="Parsing metrics…"/> : metrics.error ? <ErrorState message={metrics.error}/> : <><div className="metric-grid"><MetricCard label="Total return" value={percent(m.total_return)}/><MetricCard label="Ending equity" value={money(m.ending_capital)}/><MetricCard label="Total P&L" value={money(m.total_pnl)}/><MetricCard label="Trades" value={String(m.total_trades ?? 'Unavailable')}/><MetricCard label="Win rate" value={percent(m.win_rate)}/><MetricCard label="Profit factor" value={number(m.profit_factor)}/><MetricCard label="Maximum drawdown" value={percent(m.maximum_drawdown)}/><MetricCard label="Sharpe" value={number(m.sharpe)}/><MetricCard label="Sortino" value={number(m.sortino)}/><MetricCard label="Exposure" value={percent(m.market_exposure)}/><MetricCard label="Execution cost" value={money(m.total_modeled_execution_cost)}/></div><ProvenancePanel provenance={metrics.data?.provenance ?? run.provenance}/></>}</>
}
