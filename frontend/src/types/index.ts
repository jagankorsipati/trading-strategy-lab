export type Strategy = {
  id: string; name: string; status: string; frozen: boolean; baseline_release: string;
  source_file: string; specification: string; starting_capital: number; sizing: string;
  default_assumptions: Record<string, unknown>; key_results: Record<string, number>; conclusion: string;
}

export type Provenance = {
  source_file: string; strategy_version?: string | null; baseline_status?: string | null;
  data_period?: string | null; execution_model?: string | null; slippage_bps?: number | null;
  generated_time?: string | null; project_version: string; commit_hash?: string | null;
}

export type Run = {
  id: string; strategy: string; run_type: string; start_date?: string | null; end_date?: string | null;
  execution_model?: string | null; slippage_bps?: number | null; profitable?: boolean | null;
  starting_equity?: number | null; total_return?: number | null; source_path: string; provenance: Provenance;
}

export type Metrics = { run_id: string; metrics: Record<string, number | string | null>; provenance: Provenance }
export type Series = { run_id: string; name: string; unit: string; available: boolean; methodology?: string; points: { timestamp: string; value: number }[] }
export type Trade = {
  id: number; symbol: string; direction: string; entry_timestamp: string; entry_price: number;
  exit_timestamp: string; exit_price: number; quantity: number; stop_price: number;
  take_profit_price: number; fees: number; slippage: number; realized_pnl: number;
  return_pct: number; exit_reason: string; holding_minutes: number; modeled_execution_cost: number;
}
export type Study = { id: string; strategy: string; run_id: string; source_path: string }
export type WalkDetail = Study & { config: Record<string, unknown>; summary: Record<string, any>; windows: Record<string, string>[]; periods: Record<string, string>[] }
export type ExecutionScenario = Record<string, any> & {
  scenario: string; total_return?: number | string; profit_factor?: number | string;
  maximum_drawdown?: number | string; total_modeled_execution_cost?: number | string;
  spread_cost?: number | string; slippage_cost?: number | string; impact_cost?: number | string;
  latency_cost?: number | string; commissions?: number | string; fully_filled_entries?: number;
  partially_filled_entries?: number; unfilled_entries?: number; rejected_entries?: number;
}
export type ExecutionDetail = Study & { config: Record<string, any>; scenarios: ExecutionScenario[] }
export type Report = { id: string; title: string; category: string; source_path: string; markdown?: string; raw_html_enabled?: boolean }
