"""
ACCA Governance Performance Microbenchmark

Purpose
-------
Measure the local computational overhead introduced by governance itself.

This benchmark intentionally excludes:
    - LLM inference
    - network calls
    - market-data retrieval
    - broker latency
    - SIEM/EDR API latency
    - disk I/O
    - database access

Measured operations
-------------------
1. SGP authorization decision
2. ACCA steady-state SOC action decision
3. ACCA non-material context observation
4. ACCA material change + assurance/authority recalculation
5. ACCA recovery change + assurance/authority recalculation

The objective is not to claim production-scale performance.
It provides an implementation-level estimate of local governance overhead.
"""

from __future__ import annotations

import argparse
import statistics
import time
from dataclasses import dataclass

from governance.demo_acca_soc import (
    EDR_DEGRADED,
    EDR_HEALTHY,
    _isolate_endpoint_request,
    build_acca_soc,
)
from governance.sgp import (
    SOCAction,
    SOCEnvironment,
    SOCRequest,
    SGPAuthorizer,
    example_sgp_profile,
)


@dataclass(frozen=True)
class BenchmarkStats:
    name: str
    iterations: int

    mean_ns: float
    median_ns: float
    p95_ns: float
    p99_ns: float
    min_ns: int
    max_ns: int

    ops_per_second: float


def percentile(
    values: list[int],
    percentile_value: float,
) -> float:
    if not values:
        raise ValueError("values must not be empty")

    ordered = sorted(values)

    if len(ordered) == 1:
        return float(ordered[0])

    position = (
        percentile_value
        / 100.0
        * (len(ordered) - 1)
    )

    lower = int(position)
    upper = min(
        lower + 1,
        len(ordered) - 1,
    )

    fraction = position - lower

    return (
        ordered[lower]
        + (
            ordered[upper]
            - ordered[lower]
        )
        * fraction
    )


def summarize(
    name: str,
    samples: list[int],
) -> BenchmarkStats:
    mean_ns = statistics.fmean(samples)
    median_ns = statistics.median(samples)

    return BenchmarkStats(
        name=name,
        iterations=len(samples),
        mean_ns=mean_ns,
        median_ns=median_ns,
        p95_ns=percentile(
            samples,
            95,
        ),
        p99_ns=percentile(
            samples,
            99,
        ),
        min_ns=min(samples),
        max_ns=max(samples),
        ops_per_second=(
            1_000_000_000.0
            / mean_ns
            if mean_ns > 0
            else float("inf")
        ),
    )


def measure(
    name: str,
    iterations: int,
    operation,
    *,
    warmup: int = 1_000,
) -> BenchmarkStats:
    for _ in range(warmup):
        operation()

    samples: list[int] = []

    for _ in range(iterations):
        start = time.perf_counter_ns()

        operation()

        end = time.perf_counter_ns()

        samples.append(
            end - start
        )

    return summarize(
        name,
        samples,
    )


def benchmark_sgp_authorization(
    iterations: int,
) -> BenchmarkStats:
    profile = example_sgp_profile()
    authorizer = SGPAuthorizer(
        profile
    )

    request = SOCRequest(
        actor_id="soc_agent",
        action=SOCAction.ISOLATE_ENDPOINT.value,
        resource_id="WORKSTATION-17",
        resource_type="endpoint",
        environment=SOCEnvironment.PRODUCTION,
    )

    return measure(
        "SGP authorization",
        iterations,
        lambda: authorizer.authorize(
            request
        ),
    )


def benchmark_acca_steady_state_decision(
    iterations: int,
) -> BenchmarkStats:
    (
        _context,
        _evidence,
        _graph,
        control,
        _engine,
    ) = build_acca_soc()

    request = _isolate_endpoint_request()

    return measure(
        "ACCA steady-state SOC decision",
        iterations,
        lambda: control.decide_action(
            request
        ),
    )


def benchmark_non_material_change(
    iterations: int,
) -> BenchmarkStats:
    (
        context,
        _evidence,
        _graph,
        _control,
        engine,
    ) = build_acca_soc()

    # This dependency is not used by assurance evidence.
    context.set(
        "dashboard_theme",
        "light",
    )

    state = {
        "value": "light",
    }

    def operation():
        next_value = (
            "dark"
            if state["value"] == "light"
            else "light"
        )

        engine.observe_context(
            "dashboard_theme",
            next_value,
        )

        state["value"] = next_value

    return measure(
        "ACCA non-material context change",
        iterations,
        operation,
    )


def benchmark_material_change(
    iterations: int,
) -> BenchmarkStats:
    (
        _context,
        _evidence,
        _graph,
        _control,
        engine,
    ) = build_acca_soc()

    state = {
        "value": EDR_HEALTHY,
    }

    def operation():
        next_value = (
            EDR_DEGRADED
            if state["value"] == EDR_HEALTHY
            else EDR_HEALTHY
        )

        engine.observe_context(
            "edr_telemetry",
            next_value,
        )

        state["value"] = next_value

    return measure(
        "ACCA material change + authority recalculation",
        iterations,
        operation,
    )


def benchmark_epoch_check(
    iterations: int,
) -> BenchmarkStats:
    (
        _context,
        _evidence,
        _graph,
        control,
        _engine,
    ) = build_acca_soc()

    current_epoch = control.authority.epoch

    # The SOC PoC adapter does not expose assert_epoch, so this benchmark
    # measures a direct equality check equivalent to the current-epoch
    # validation semantics.
    def operation():
        if current_epoch != control.authority.epoch:
            raise RuntimeError(
                "stale epoch"
            )

    return measure(
        "Authority epoch check",
        iterations,
        operation,
    )


def ns_to_us(value: float) -> float:
    return value / 1_000.0


def print_stats(
    stats: BenchmarkStats,
) -> None:
    print()
    print(stats.name)
    print("-" * len(stats.name))

    print(
        f"Iterations:        "
        f"{stats.iterations:,}"
    )

    print(
        f"Mean:              "
        f"{ns_to_us(stats.mean_ns):,.3f} us"
    )

    print(
        f"Median:            "
        f"{ns_to_us(stats.median_ns):,.3f} us"
    )

    print(
        f"P95:               "
        f"{ns_to_us(stats.p95_ns):,.3f} us"
    )

    print(
        f"P99:               "
        f"{ns_to_us(stats.p99_ns):,.3f} us"
    )

    print(
        f"Min:               "
        f"{ns_to_us(stats.min_ns):,.3f} us"
    )

    print(
        f"Max:               "
        f"{ns_to_us(stats.max_ns):,.3f} us"
    )

    print(
        f"Throughput:        "
        f"{stats.ops_per_second:,.0f} ops/s"
    )


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--iterations",
        type=int,
        default=50_000,
    )

    args = parser.parse_args()

    iterations = args.iterations

    print()
    print("=" * 76)
    print(
        "ACCA GOVERNANCE PERFORMANCE MICROBENCHMARK"
    )
    print("=" * 76)

    print()
    print(
        "Local in-process benchmark; excludes model, network, "
        "broker, SIEM/EDR, database, and disk latency."
    )

    results = [
        benchmark_sgp_authorization(
            iterations
        ),

        benchmark_acca_steady_state_decision(
            iterations
        ),

        benchmark_epoch_check(
            iterations
        ),

        benchmark_non_material_change(
            iterations
        ),

        benchmark_material_change(
            iterations
        ),
    ]

    for result in results:
        print_stats(
            result
        )

    print()
    print("=" * 76)
    print("SUMMARY")
    print("=" * 76)

    print()

    print(
        f"{'Operation':48} "
        f"{'Mean us':>12} "
        f"{'P95 us':>12} "
        f"{'Ops/s':>14}"
    )

    print(
        "-" * 90
    )

    for result in results:
        print(
            f"{result.name:48} "
            f"{ns_to_us(result.mean_ns):12.3f} "
            f"{ns_to_us(result.p95_ns):12.3f} "
            f"{result.ops_per_second:14,.0f}"
        )


if __name__ == "__main__":
    main()
