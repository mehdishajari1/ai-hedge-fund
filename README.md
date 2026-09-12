# AI Hedge Fund

This is a proof of concept for an AI-powered hedge fund. The goal of this project is to explore the use of AI to make trading decisions. This project is for **educational** purposes only and is not intended for real trading or investment.

> **🚧 The project is evolving.** We're rebuilding it into a persistent, always-on AI hedge fund — a *fund* as a first-class entity you can backtest, paper-trade, and (opt-in) run live, with the investor agents reimagined as pluggable, backtestable "alpha models." Read the **[Vision →](VISION.md)** and the **[Roadmap →](ROADMAP.md)**.

Note: the system does not actually make any trades.

## ACCA Governance Research Artifact

This repository also contains the research implementation used to evaluate
**Assurance-Conditioned Continuous Authorization (ACCA)** for autonomous AI
agents.

The governance layer integrates runtime assurance and authorization with the
AI Hedge Fund execution path. In the Trading Governance Profile (TGP),
governance is enforced at the consequence boundary between proposed orders
and broker execution. The implementation includes assurance evidence,
material-change detection, authority derivation, authority epochs, and
policy-enforcement mechanisms.

The cleaned ACCA Paper 1 artifact contains **93 non-duplicated governance
tests**: 25 domain-independent ACCA/core tests, 48 TGP/trading tests, and
20 preliminary synthetic Security Governance Profile (SGP/SOC) tests.
The SGP/SOC tests are exploratory software tests and are not evidence of
operational SOC validation or empirical cross-domain generalization.

For the governance architecture, integration points, execution path, and
reproduction instructions, see
[`GOVERNANCE_INTEGRATION.md`](GOVERNANCE_INTEGRATION.md).

The reproducible paper artifact is frozen under the Git tag
`acca-paper-v1.1`.

[![Twitter Follow](https://img.shields.io/twitter/follow/virattt?style=social)](https://twitter.com/virattt)

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