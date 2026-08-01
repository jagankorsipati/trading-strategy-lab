import { cleanup, render, screen, waitFor } from '@testing-library/react'
function MemoryRouter({ children }: { children: React.ReactNode }) { return children }
import { afterEach, describe, expect, it, vi } from 'vitest'
import { EmptyState, ErrorState, LoadingState, ResearchNotice } from '../components/ui'
import { StrategiesPage } from '../pages/StrategiesPage'

const strategy = {
  id: 'orb-v1', name: 'ORB-v1', status: 'FROZEN BASELINE', frozen: true,
  baseline_release: 'v0.1.0-research-foundation', source_file: 'src/trading_lab/strategies/orb.py',
  specification: 'docs/ORB_V1_SPEC.md', starting_capital: 10000,
  sizing: 'One share per trade', default_assumptions: { opening_range_minutes: 15 },
  key_results: { zero_bps_return: 0.2, two_bps_return: -0.1, five_bps_return: -0.4 },
  conclusion: 'Not friction resistant.',
}

afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('research dashboard states', () => {
  it('shows the research disclaimer', () => {
    render(<ResearchNotice/>)
    expect(screen.getByText('Research and educational use only.')).toBeInTheDocument()
    expect(screen.getByText(/does not guarantee future results/i)).toBeInTheDocument()
  })
  it('renders a deterministic loading state', () => {
    render(<LoadingState label="Cataloging evidence"/>)
    expect(screen.getByText('Cataloging evidence')).toBeInTheDocument()
  })
  it('renders an explicit empty state', () => {
    render(<EmptyState label="No runs found"/>)
    expect(screen.getByText('No runs found')).toBeInTheDocument()
  })
  it('renders an API error without a stack trace', () => {
    render(<ErrorState message="Artifact could not be parsed"/>)
    expect(screen.getByText('Artifact could not be parsed')).toBeInTheDocument()
    expect(screen.queryByText(/traceback/i)).not.toBeInTheDocument()
  })
  it('shows frozen strategy metadata and friction outcomes', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [strategy] }))
    render(<MemoryRouter><StrategiesPage/></MemoryRouter>)
    expect(await screen.findByRole('heading', { name: 'ORB-v1' })).toBeInTheDocument()
    expect(screen.getByText('FROZEN BASELINE')).toBeInTheDocument()
    expect(screen.getByText('20%')).toBeInTheDocument()
    expect(screen.getByText('-10%')).toBeInTheDocument()
    expect(screen.getByText('Not friction resistant.')).toBeInTheDocument()
  })
  it('shows empty catalog behavior', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [] }))
    render(<MemoryRouter><StrategiesPage/></MemoryRouter>)
    expect(await screen.findByText('No matching artifacts are available.')).toBeInTheDocument()
  })
  it('surfaces API failures to the researcher', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({ detail: { message: 'Malformed artifact' } }) }))
    render(<MemoryRouter><StrategiesPage/></MemoryRouter>)
    expect(await screen.findByText('Malformed artifact')).toBeInTheDocument()
  })
  it('links strategy evidence to a report path', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [strategy] }))
    render(<MemoryRouter><StrategiesPage/></MemoryRouter>)
    expect(await screen.findByRole('link', { name: /open specification/i })).toHaveAttribute('href')
  })
  it('does not expose editing controls for a frozen strategy', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [strategy] }))
    render(<MemoryRouter><StrategiesPage/></MemoryRouter>)
    await screen.findByText('ORB-v1')
    expect(screen.queryByRole('button', { name: /save|optimize|edit/i })).not.toBeInTheDocument()
  })
  it('requests the versioned read-only strategy endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [strategy] })
    vi.stubGlobal('fetch', fetchMock)
    render(<MemoryRouter><StrategiesPage/></MemoryRouter>)
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/strategies')
    expect(fetchMock.mock.calls[0][1]).toEqual({ headers: { Accept: 'application/json' } })
  })
})
