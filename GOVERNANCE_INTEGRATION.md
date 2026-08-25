# Governance integration — Increment 1

This branch adds an **assurance-conditioned authority control plane** to the v2 fund pipeline without giving LLM analyst personas direct trading authority.

## Architecture

`signals -> portfolio -> financial risk -> build_orders -> governance gateway -> broker -> ledger`

The governance layer is deliberately outside model reasoning. `risk/` still answers whether a portfolio is financially acceptable. `governance/` answers whether the fund is currently authorized to cause the proposed action.

## Components

- `hedge_fund/governance/models.py` — Authority Vector, assurance claims, material changes, decisions, audit record.
- `hedge_fund/governance/control.py` — approved baseline authority, evidence invalidation, authority recalculation, authority epochs, reauthorization.
- `hedge_fund/governance/gateway.py` — runtime consequence boundary immediately before `Broker.place_order()`.
- `CycleRecord.governance` — governance state and decisions become part of the cycle's serialized audit truth.

## Run the existing application unchanged

Governance is opt-in in this increment, so existing callers of `run_cycle(...)` behave exactly as before.

## Run a governed cycle

```python
from hedge_fund.governance import GovernanceControlPlane

governance = GovernanceControlPlane.paper_trading_default(
    fund.spec.name,
    max_order_value=5_000,
)

record = run_cycle(
    fund, as_of, broker, data_client, universe,
    governance=governance,
)

print(record.governance.model_dump_json(indent=2))
```

## Trigger a material change

```python
from hedge_fund.governance import MaterialChange

governance.apply_material_change(MaterialChange(
    change_type="model_substitution",
    dependency="model",
    description="Portfolio-relevant LLM/model configuration changed",
))
```

This invalidates `MODEL_ASSURANCE`, increments the authority epoch, and contracts effective authority so `paper_order` is no longer allowed.

A subsequent cycle still records the proposed orders, but the governance gateway denies execution. This is intentional: the audit record preserves what the fund wanted to do and why execution was blocked.

## Reauthorize

After the required evaluation/evidence is refreshed:

```python
governance.set_claim_healthy("MODEL_ASSURANCE", "evaluation passed")
```

The controller recalculates from the governance-approved baseline, increments the epoch again, and restores paper-order authority if all required claims are healthy.

## Preemption semantics

`assert_epoch()` invalidates authorization made under an older authority epoch. The current `SimBroker.place_order()` is synchronous and atomic, so the gateway checks immediately before that call.

When a future paper/live broker has asynchronous states, the same epoch check should be made at each consequential transition, especially immediately before an irreversible commit. The desired semantics are:

- proposed -> deny
- approved but not dispatched -> invalidate
- dispatched but cancellable -> cancel
- partially filled -> stop remainder and reconcile
- irreversibly committed -> contain/reconcile and deny further actions

This is the first implementation of **material change -> evidence invalidation -> authority recalculation -> immediate enforcement -> reauthorization**.

## Tests

Run the new governance + integration tests:

```powershell
poetry run pytest hedge_fund/governance hedge_fund/pipeline
```

Run the complete project suite:

```powershell
poetry run pytest hedge_fund/
```

The uploaded baseline had 175 passing tests and 38 skipped in the user's Poetry environment. This modified copy adds 8 tests (6 governance unit tests + 2 pipeline integration tests). In the build container, all governance/pipeline/risk/broker tests pass; the full suite reaches 174 passing + 38 skipped, with 9 unrelated LLM-client failures because this container does not have the repository's LangChain provider packages installed. Run the full suite in the existing Poetry environment on the user's machine for the authoritative result.
