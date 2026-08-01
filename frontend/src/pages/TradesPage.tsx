import { useEffect, useState } from 'react'
import { useApi } from '../api/useApi'
import { EmptyState, ErrorState, LoadingState, PageHeader, Panel } from '../components/ui'
import type { Run, Trade } from '../types'
import { money, percent } from '../utils/format'

export function TradesPage() {
  const runs = useApi<{ items: Run[] }>('/runs?run_type=standard_backtest&page_size=100')
  const [runId,setRunId] = useState('')
  const [direction,setDirection] = useState('')
  const [outcome,setOutcome] = useState('')
  const [page,setPage] = useState(1)
  useEffect(() => { if (!runId && runs.data?.items.length) setRunId(runs.data.items[0].id) }, [runs.data,runId])
  const query = new URLSearchParams({ page: String(page), page_size: '25', sort_by: 'entry_timestamp', order: 'desc' })
  if (direction) query.set('direction', direction)
  if (outcome) query.set('outcome', outcome)
  const trades = useApi<{ items: Trade[]; total: number; page: number; page_size: number }>(runId ? `/runs/${runId}/trades?${query}` : null)
  return <><PageHeader eyebrow="Trade-level evidence" title="Trade explorer">Search the fields actually recorded by the backtester. Intrabar candle paths and queue position are unavailable.</PageHeader><Panel className="filters"><label>Run<select value={runId} onChange={e => {setRunId(e.target.value);setPage(1)}}>{runs.data?.items.map(run => <option key={run.id} value={run.id}>{run.strategy} · {run.start_date}</option>)}</select></label><label>Direction<select value={direction} onChange={e => {setDirection(e.target.value);setPage(1)}}><option value="">All directions</option><option value="long">Long</option><option value="short">Short</option></select></label><label>Outcome<select value={outcome} onChange={e => {setOutcome(e.target.value);setPage(1)}}><option value="">All outcomes</option><option value="winner">Winners</option><option value="loser">Losers</option><option value="breakeven">Breakeven</option></select></label></Panel>{runs.loading || trades.loading ? <LoadingState/> : runs.error || trades.error ? <ErrorState message={runs.error ?? trades.error ?? 'Unable to load trades'}/> : !trades.data?.items.length ? <EmptyState label="No trades match these filters."/> : <Panel className="table-panel"><div className="table-scroll"><table><thead><tr><th>Date</th><th>Side</th><th>Entry</th><th>Exit</th><th>Qty</th><th>P&L</th><th>Return</th><th>Stop</th><th>Target</th><th>Reason</th><th>Hold</th><th>Cost</th></tr></thead><tbody>{trades.data.items.map(trade => <tr key={trade.id}><td>{trade.entry_timestamp.slice(0,10)}</td><td><span className="direction-label">{trade.direction}</span></td><td>{money(trade.entry_price)}</td><td>{money(trade.exit_price)}</td><td>{trade.quantity}</td><td>{money(trade.realized_pnl)}</td><td>{percent(trade.return_pct)}</td><td>{money(trade.stop_price)}</td><td>{money(trade.take_profit_price)}</td><td>{trade.exit_reason.replaceAll('_',' ')}</td><td>{trade.holding_minutes}m</td><td>{money(trade.modeled_execution_cost)}</td></tr>)}</tbody></table></div><div className="pagination"><span>{trades.data.total} trades</span><button disabled={page===1} onClick={() => setPage(page-1)}>Previous</button><span>Page {page}</span><button disabled={page*25>=trades.data.total} onClick={() => setPage(page+1)}>Next</button></div></Panel>}</>
}
