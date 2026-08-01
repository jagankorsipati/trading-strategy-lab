import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { useApi } from '../api/useApi'
import { EmptyState, ErrorState, LoadingState, PageHeader, Panel } from '../components/ui'
import type { Report } from '../types'

export function ReportsPage() {
  const reports = useApi<Report[]>('/reports')
  const [id,setId] = useState('')
  useEffect(() => { if (!id && reports.data?.length) setId(reports.data[0].id) }, [reports.data,id])
  const detail = useApi<Report>(id ? `/reports/${id}` : null)
  if (reports.loading) return <LoadingState/>
  if (reports.error) return <ErrorState message={reports.error}/>
  if (!reports.data?.length) return <EmptyState label="No Markdown reports were discovered."/>
  return <><PageHeader eyebrow="Source documentation" title="Research reports">Markdown is rendered without raw HTML execution. Every document remains traceable to its repository path.</PageHeader><div className="report-layout"><Panel className="report-list">{reports.data.map(report => <button className={id===report.id?'active':''} key={report.id} onClick={() => setId(report.id)}><strong>{report.title}</strong><span>{report.category}</span><small>{report.source_path}</small></button>)}</Panel><Panel className="report-content">{detail.loading ? <LoadingState/> : detail.error ? <ErrorState message={detail.error}/> : <><div className="report-source">Source: <code>{detail.data?.source_path}</code> · Raw HTML disabled</div><article className="markdown"><ReactMarkdown>{detail.data?.markdown ?? ''}</ReactMarkdown></article></>}</Panel></div></>
}
