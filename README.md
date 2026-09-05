# AI Hedge Fund

This is a proof of concept for an AI-powered hedge fund. The goal of this project is to explore the use of AI to make trading decisions. This project is for **educational** purposes only and is not intended for real trading or investment.

> **🚧 The project is evolving.** We're rebuilding it into a persistent, always-on AI hedge fund — a *fund* as a first-class entity you can backtest, paper-trade, and (opt-in) run live, with the investor agents reimagined as pluggable, backtestable "alpha models." Read the **[Vision →](VISION.md)** and the **[Roadmap →](ROADMAP.md)**.

Note: the system does not actually make any trades.

[![Twitter Follow](https://img.shields.io/twitter/follow/virattt?style=social)](https://twitter.com/virattt)


## ACCA Research Artifact

This repository contains the reference implementation and experimental
artifacts accompanying the paper:

**Assurance-Conditioned Continuous Authorization for Autonomous AI Agents**

The ACCA work extends the AI Hedge Fund codebase with a governance control
plane for assurance-conditioned authority in autonomous AI agents. The
trading application provides one evaluation domain, while a Security
Operations Governance Profile (SGP) provides a second cross-domain
evaluation.

### Frozen experimental checkpoint

The experimental results reported in the paper correspond to:

- **Tag:** `acca-paper-v1.0`
- **Commit:** `1e42dbfb727a8ae647665f0e2f2f3b955e80025a`
- **Python:** 3.11.0
- **Poetry:** 2.4.1
- **Governance test suite:** 100 passing tests

### Artifact structure

The ACCA implementation and experiments are located under:

- `hedge_fund/governance/` — ACCA governance implementation,
  governance profiles, evidence handling, materiality detection,
  authority management, and experimental scenarios.
- `hedge_fund/tests/governance/` — ACCA, TGP, SGP, and experimental
  scenario tests.

### Reproducing the reported governance tests

Clone the repository and check out the frozen experimental artifact:

    git clone https://github.com/mehdishajari1/ai-hedge-fund.git
    cd ai-hedge-fund
    git checkout acca-paper-v1.0

Install the frozen dependencies:

    poetry install

Then run the governance test suite from the `hedge_fund` directory:

    cd hedge_fund
    poetry run python -m pytest governance tests/governance -q

Expected result:

    100 passed

### Reproducing the ACCA microbenchmark

From the `hedge_fund` directory:

    poetry run python -m governance.benchmark_acca

The benchmark measures local in-process governance operations and excludes
model, network, broker, SIEM/EDR, database, and disk latency. Absolute
timings therefore depend on the execution environment and should not be
interpreted as end-to-end agent latency.

### Paper

M. Shajari, *Assurance-Conditioned Continuous Authorization for Autonomous
AI Agents*.

The arXiv link will be added after publication.


## Disclaimer

This project is for **educational and research purposes only**.

- Not intended for real trading or investment
- No investment advice or guarantees provided
- Creator assumes no liability for financial losses
- Consult a financial advisor for investment decisions
- Past performance does not indicate future results

By using this software, you agree to use it solely for learning purposes.

## How to Install

```bash
pipx install aihf
```

(or `uv tool install aihf`, or `pip install aihf` into an environment of your choice)

Then run it from anywhere:

```bash
aihf
```

### API keys

The app asks for keys the first time it needs them and saves them to `~/.hedge-fund/.env` — nothing to configure up front. It needs:

- A [Financial Datasets](https://financialdatasets.ai) API key, for prices, fundamentals, and earnings.
- One LLM API key for the LLM-powered alpha models. Supported providers: Anthropic, OpenAI, DeepSeek, Google, xAI, Kimi.

Keys exported in your shell always win over the saved file.

## How to Run

### Interactive app

```bash
aihf
```

With no arguments, this launches the interactive terminal app. Build a fund — pick stocks, strategies, rebalance cadence — or backtest a saved fund and watch its equity curve draw against its benchmark. Funds you build are saved as mandate files in `~/.hedge-fund/mandates/`.

### Non-interactive

Run one fund cycle from a mandate file. The full cycle record prints to stdout as JSON; a short human summary goes to stderr:

```bash
aihf ~/.hedge-fund/mandates/example.yaml --tickers AAPL,MSFT
```

Backtest the mandate over history at its rebalance cadence:

```bash
aihf ~/.hedge-fund/mandates/example.yaml --tickers AAPL,MSFT --backtest
```

A mandate is the desk — strategies, staff, risk, capital, cadence — and never names tickers; `--tickers` says what to point it at for this run.

## Development

```bash
git clone https://github.com/virattt/ai-hedge-fund.git
cd ai-hedge-fund
poetry install
poetry run aihf
poetry run pytest hedge_fund
```

## How to Contribute

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

**Important**: Please keep your pull requests small and focused. This will make it easier to review and merge.

## Feature Requests

If you have a feature request, please open an [issue](https://github.com/virattt/ai-hedge-fund/issues) and make sure it is tagged with `enhancement`.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
