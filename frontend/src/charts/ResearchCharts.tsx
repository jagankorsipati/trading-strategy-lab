import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const tooltipStyle = { background: '#102024', border: '1px solid #2f4549', borderRadius: 8, color: '#fff' }

export function LineSeriesChart({ data, unit, label }: { data: { timestamp: string; value: number }[]; unit: string; label: string }) {
  return <div className="chart" aria-label={label}><ResponsiveContainer width="100%" height={280}><LineChart data={data}><CartesianGrid strokeDasharray="3 3" stroke="#d9ddd8"/><XAxis dataKey="timestamp" tickFormatter={v => String(v).slice(0,7)} minTickGap={40}/><YAxis tickFormatter={v => unit === 'percent' ? `${(v*100).toFixed(0)}%` : `$${Math.round(v/1000)}k`}/><Tooltip contentStyle={tooltipStyle}/><Line type="linear" dataKey="value" stroke="#0d766e" dot={false} strokeWidth={2}/></LineChart></ResponsiveContainer></div>
}
export function ScenarioBarChart({ data, dataKey = 'returnValue', label = 'Scenario return' }: { data: Record<string, any>[]; dataKey?: string; label?: string }) {
  return <div className="chart" aria-label={label}><ResponsiveContainer width="100%" height={320}><BarChart data={data}><CartesianGrid strokeDasharray="3 3" stroke="#d9ddd8"/><XAxis dataKey="scenario" angle={-20} textAnchor="end" height={75}/><YAxis tickFormatter={v => `${(v*100).toFixed(0)}%`}/><Tooltip contentStyle={tooltipStyle}/><Bar dataKey={dataKey}>{data.map((item,index) => <Cell key={index} fill={item[dataKey] >= 0 ? '#0d766e' : '#c88735'}/>)}</Bar></BarChart></ResponsiveContainer></div>
}
export function CostBarChart({ data }: { data: Record<string, any>[] }) {
  return <div className="chart" aria-label="Modeled execution cost breakdown"><ResponsiveContainer width="100%" height={320}><BarChart data={data}><CartesianGrid strokeDasharray="3 3" stroke="#d9ddd8"/><XAxis dataKey="scenario" angle={-20} textAnchor="end" height={75}/><YAxis tickFormatter={v => `$${Math.round(v/1000)}k`}/><Tooltip contentStyle={tooltipStyle}/><Bar dataKey="spread" stackId="a" fill="#275d68"/><Bar dataKey="slippage" stackId="a" fill="#0d766e"/><Bar dataKey="impact" stackId="a" fill="#7a8f57"/><Bar dataKey="latency" stackId="a" fill="#c88735"/><Bar dataKey="commission" stackId="a" fill="#8d6b91"/></BarChart></ResponsiveContainer></div>
}
