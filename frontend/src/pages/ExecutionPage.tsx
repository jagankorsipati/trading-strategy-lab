import { useEffect, useMemo, useState } from 'react'
import { useApi } from '../api/useApi'
import { CostBarChart, ScenarioBarChart } from '../charts/ResearchCharts'
import { Badge, EmptyState, ErrorState, LoadingState, PageHeader, Panel } from '../components/ui'
import type { ExecutionDetail, Study } from '../types'
import { asNumber, money, percent } from '../utils/format'

export function ExecutionPage() {
  const studies = useApi<Study[]>('/execution-studies')
  const [id,setId] = useState('')
  useEffect(() => { if (!id && studies.data?.length) setId(studies.data[0].id) }, [studies.data,id])
  const detail = useApi<ExecutionDetail>(id ? `/execution-studies/${id}` : null)
  const rows = useMemo(() => (detail.data?.scenarios ?? []).map(row => ({
    ...row, returnValue: asNumber(row.total_return) ?? 0,
    spread: asNumber(row.spread_cost) ?? 0, slippage: asNumber(row.slippage_cost) ?? 0,
    impact: asNumber(row.impact_cost) ?? 0, latency: asNumber(row.latency_cost) ?? 0,
    commission: asNumber(row.commissions) ?? 0,
  })), [detail.data])
  if (studies.loading) return <LoadingState/>
  if (studies.error) return <ErrorState message={studies.error}/>
  if (!studies.data?.length) return <EmptyState label="No execution studies were discovered."/>
  return <><PageHeader eyebrow="Modeled fill sensitivity" title="Execution study">Spread, impact, latency, and order-touch assumptions are proxies—not observed historical quotes or broker fills.</PageHeader><Panel className="filters"><label>Study<select value={id} onChange={e => setId(e.target.value)}>{studies.data.map(study => <option key={study.id} value={study.id}>{study.strategy} · {study.run_id}</option>)}</select></label><Badge tone="warning">Modeled, not observed</Badge></Panel>{detail.loading ? <LoadingState/> : detail.error ? <ErrorState message={detail.error}/> : <><div className="chart-grid"><Panel><h2>Total return by model</h2><ScenarioBarChart data={rows}/></Panel><Panel><h2>Execution cost breakdown</h2><CostBarChart data={rows}/></Panel></div><Panel className="table-panel"><div className="table-scroll"><table><thead><tr><th>Scenario</th><th>Return</th><th>PF</th><th>Max DD</th><th>Cost</th><th>Full</th><th>Partial</th><th>Unfilled</th><th>Rejected</th></tr></thead><tbody>{rows.map(row => <tr key={row.scenario}><td><strong>{row.scenario}</strong></td><td>{percent(asNumber(row.total_return))}</td><td>{Number(row.profit_factor).toFixed(2)}</td><td>{percent(asNumber(row.maximum_drawdown))}</td><td>{money(asNumber(row.total_modeled_execution_cost))}</td><td>{row.fully_filled_entries}</td><td>{row.partially_filled_entries}</td><td>{row.unfilled_entries}</td><td>{row.rejected_entries}</td></tr>)}</tbody></table></div></Panel><Panel><h2>Scenario assumptions</h2><div className="assumption-grid">{Object.entries(detail.data?.config.assumptions ?? {}).filter(([key]) => key !== 'study_period').map(([name,value]) => <div key={name}><strong>{name}</strong><pre>{JSON.stringify(value,null,2)}</pre></div>)}</div></Panel></>}</>
}
