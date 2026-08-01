import { useEffect, useMemo, useState } from 'react'
import { useApi } from '../api/useApi'
import { ScenarioBarChart } from '../charts/ResearchCharts'
import { Badge, EmptyState, ErrorState, LoadingState, MetricCard, PageHeader, Panel } from '../components/ui'
import type { Study, WalkDetail } from '../types'
import { asNumber, percent } from '../utils/format'

export function WalkForwardPage() {
  const studies = useApi<Study[]>('/walk-forward')
  const [id,setId] = useState('')
  const [friction,setFriction] = useState('2.0')
  useEffect(() => { if (!id && studies.data?.length) setId(studies.data[0].id) }, [studies.data,id])
  const detail = useApi<WalkDetail>(id ? `/walk-forward/${id}` : null)
  const oos = useMemo(() => (detail.data?.periods ?? []).filter(p => p.purpose === 'out_of_sample' && Number(p.friction_bps) === Number(friction)), [detail.data,friction])
  const scenario = detail.data?.summary?.scenarios?.[friction]
  if (studies.loading) return <LoadingState/>
  if (studies.error) return <ErrorState message={studies.error}/>
  if (!studies.data?.length) return <EmptyState label="No walk-forward studies were discovered."/>
  return <><PageHeader eyebrow="Chronology protected" title="Walk-forward analysis">Fixed-strategy rolling evaluation. No strategy fitting or optimization occurred.</PageHeader><Panel className="filters"><label>Study<select value={id} onChange={e => setId(e.target.value)}>{studies.data.map(study => <option key={study.id} value={study.id}>{study.strategy} · {study.run_id}</option>)}</select></label><label>Friction<select value={friction} onChange={e => setFriction(e.target.value)}><option value="0.0">0 bps</option><option value="2.0">2 bps</option><option value="5.0">5 bps</option></select></label><Badge tone="info">OOS is primary</Badge></Panel>{detail.loading ? <LoadingState/> : detail.error ? <ErrorState message={detail.error}/> : <><div className="metric-grid compact"><MetricCard label="OOS windows" value={String(scenario?.out_of_sample_periods ?? oos.length)}/><MetricCard label="Profitable OOS" value={`${scenario?.profitable_periods ?? 'Unavailable'}/${scenario?.out_of_sample_periods ?? oos.length}`}/><MetricCard label="Compounded OOS return" value={percent(scenario?.compounded_out_of_sample_return)}/><MetricCard label="Quality findings" value={String(scenario?.periods_with_quality_findings ?? 'Unavailable')}/></div><Panel className="oos-panel"><div className="section-title"><div><p className="eyebrow">Primary evidence</p><h2>Out-of-sample return by window</h2></div><span className="unit-label">{friction} bps · percentage return</span></div><ScenarioBarChart data={oos.map(period => ({ scenario: `Window ${period.window_id} · ${period.start_date.slice(0,4)}`, returnValue: asNumber(period.total_return) ?? 0 }))}/></Panel><Panel><h2>Chronological windows</h2><div className="window-list">{detail.data?.windows.map(window => <div key={window.window_id}><strong>Window {window.window_id}</strong><span><b>Research</b>{window.research_start} — {window.research_end}</span><span><b>Validation</b>{window.validation_start} — {window.validation_end}</span><span className="oos"><b>Out-of-sample</b>{window.out_of_sample_start} — {window.out_of_sample_end}</span></div>)}</div><p className="method">Missing-bar findings remain attached to their source periods; no candles are manufactured.</p></Panel></>}</>
}
