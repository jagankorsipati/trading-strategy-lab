from trading_lab.api.models.responses import StrategyResponse


CONCLUSION = (
    "Positive gross results do not survive modest modeled friction consistently; "
    "not supported as a strategy-driven paper-trading candidate."
)

STRATEGIES = {
    "orb-v1": StrategyResponse(
        id="orb-v1", name="ORB-v1", status="FROZEN", frozen=True,
        baseline_release="v0.1.0-research-foundation",
        source_file="src/trading_lab/strategies/orb.py",
        specification="docs/ORB-v1.md", starting_capital=10_000,
        sizing="Fixed 10 shares, subject to conservative buying power",
        default_assumptions={"opening_range_minutes": 15, "confirmation": "close", "stop_pct": 0.005, "target_pct": 0.01, "maximum_trades_per_day": 1},
        key_results={"zero_bps_return": 0.196381511, "two_bps_return": -0.044641173, "five_bps_return": -0.415176097},
        conclusion=CONCLUSION,
    ),
    "reference-orb-v1": StrategyResponse(
        id="reference-orb-v1", name="Reference-ORB-v1", status="FROZEN", frozen=True,
        baseline_release="v0.1.0-research-foundation",
        source_file="src/trading_lab/strategies/reference_orb.py",
        specification="docs/Reference-ORB-v1.md", starting_capital=25_000,
        sizing="1% fixed-account risk, 4x notional cap, integer shares and buying power",
        default_assumptions={"opening_candle_minutes": 5, "reward_risk_multiple": 10, "commission_per_share": 0.0005, "maximum_trades_per_day": 1},
        key_results={"zero_bps_return": 0.83459174, "two_bps_return": -0.166084188, "five_bps_return": -0.742994283},
        conclusion=CONCLUSION,
    ),
}
