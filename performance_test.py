#!/usr/bin/env python3
"""
Performance test for Expense Tracker.

Simulates multiple virtual users with a fixed concurrency limit.
Default: 50 users, 10 concurrent.

Start the app first:
    .\\venv\\Scripts\\python app.py

Run:
    .\\venv\\Scripts\\python performance_test.py
    .\\venv\\Scripts\\python performance_test.py --users 50 --concurrency 10 --base-url http://127.0.0.1:5000
"""

from __future__ import annotations

import argparse
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date

import requests

DEFAULT_BASE_URL = "http://127.0.0.1:5000"
DEFAULT_USERS = 50
DEFAULT_CONCURRENCY = 10
REQUEST_TIMEOUT = 30


@dataclass
class RequestResult:
    user_id: int
    endpoint: str
    method: str
    status_code: int | None
    duration_ms: float
    success: bool
    error: str | None = None


@dataclass
class PerformanceReport:
    results: list[RequestResult] = field(default_factory=list)
    users_completed: int = 0
    users_failed: int = 0
    wall_time_sec: float = 0.0

    def add(self, result: RequestResult) -> None:
        self.results.append(result)


class MetricsCollector:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.report = PerformanceReport()

    def record(self, result: RequestResult) -> None:
        with self._lock:
            self.report.results.append(result)

    def user_finished(self, failed: bool) -> None:
        with self._lock:
            if failed:
                self.report.users_failed += 1
            else:
                self.report.users_completed += 1


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(len(ordered) * pct / 100)
    index = min(index, len(ordered) - 1)
    return ordered[index]


def timed_request(
    session: requests.Session,
    base_url: str,
    user_id: int,
    method: str,
    path: str,
    collector: MetricsCollector,
    **kwargs,
) -> requests.Response | None:
    url = f"{base_url.rstrip('/')}{path}"
    endpoint = path.split("?")[0]
    start = time.perf_counter()
    status_code = None
    error = None
    response = None

    try:
        response = session.request(
            method, url, timeout=REQUEST_TIMEOUT, **kwargs
        )
        status_code = response.status_code
        success = response.ok
    except requests.RequestException as exc:
        success = False
        error = str(exc)
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        collector.record(
            RequestResult(
                user_id=user_id,
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                duration_ms=duration_ms,
                success=success,
                error=error,
            )
        )

    return response


def simulate_user(
    user_id: int, base_url: str, collector: MetricsCollector
) -> None:
    """Typical user session: browse, list, add expense, summary, export."""
    session = requests.Session()
    today = date.today().isoformat()
    month = today[:7]
    failed = False

    steps = [
        ("GET", "/"),
        ("GET", "/api/categories"),
        ("GET", f"/api/expenses?month={month}"),
        (
            "POST",
            "/api/expenses",
            {
                "data": {
                    "amount": str(100 + user_id),
                    "description": f"Perf test expense user {user_id}",
                    "category": "Food",
                    "expense_date": today,
                }
            },
        ),
        ("GET", f"/api/summary?month={month}"),
        ("GET", "/api/expenses"),
    ]

    if user_id % 5 == 0:
        steps.append(("GET", "/api/expenses/export"))

    try:
        for step in steps:
            method = step[0]
            path = step[1]
            extra = step[2] if len(step) > 2 else {}
            response = timed_request(
                session,
                base_url,
                user_id,
                method,
                path,
                collector,
                **extra,
            )
            if response is None or not response.ok:
                failed = True
                break
    except Exception:
        failed = True
    finally:
        collector.user_finished(failed)


def check_server(base_url: str) -> bool:
    try:
        response = requests.get(base_url, timeout=5)
        return response.status_code < 500
    except requests.RequestException:
        return False


def print_report(report: PerformanceReport, users: int, concurrency: int) -> None:
    results = report.results
    total_requests = len(results)
    successes = sum(1 for r in results if r.success)
    failures = total_requests - successes

    print("\n" + "=" * 60)
    print("PERFORMANCE TEST REPORT")
    print("=" * 60)
    print(f"Virtual users:     {users}")
    print(f"Concurrency:       {concurrency}")
    print(f"Users completed:   {report.users_completed}")
    print(f"Users failed:      {report.users_failed}")
    print(f"Wall time:         {report.wall_time_sec:.2f}s")
    print(f"Total requests:    {total_requests}")
    print(f"Successful:        {successes}")
    print(f"Failed:            {failures}")
    if report.wall_time_sec > 0:
        print(f"Throughput:        {total_requests / report.wall_time_sec:.2f} req/s")

    durations = [r.duration_ms for r in results if r.success]
    if durations:
        print("\nOverall latency (successful requests, ms):")
        print(f"  Min:    {min(durations):.1f}")
        print(f"  Avg:    {statistics.mean(durations):.1f}")
        print(f"  Median: {statistics.median(durations):.1f}")
        print(f"  P95:    {percentile(durations, 95):.1f}")
        print(f"  Max:    {max(durations):.1f}")

    by_endpoint: dict[str, list[float]] = {}
    for r in results:
        if r.success:
            key = f"{r.method} {r.endpoint}"
            by_endpoint.setdefault(key, []).append(r.duration_ms)

    if by_endpoint:
        print("\nPer endpoint (avg ms | count | failures):")
        endpoint_failures: dict[str, int] = {}
        for r in results:
            if not r.success:
                key = f"{r.method} {r.endpoint}"
                endpoint_failures[key] = endpoint_failures.get(key, 0) + 1

        for key in sorted(by_endpoint):
            times = by_endpoint[key]
            fail_count = endpoint_failures.get(key, 0)
            print(
                f"  {key:<35} {statistics.mean(times):>8.1f}  "
                f"{len(times):>5}  {fail_count:>5}"
            )

    failed_results = [r for r in results if not r.success]
    if failed_results:
        print("\nSample errors (up to 5):")
        for r in failed_results[:5]:
            detail = r.error or f"HTTP {r.status_code}"
            print(f"  User {r.user_id} {r.method} {r.endpoint}: {detail}")

    print("=" * 60)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Expense Tracker performance test"
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"App base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--users",
        type=int,
        default=DEFAULT_USERS,
        help=f"Total virtual users (default: {DEFAULT_USERS})",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"Max concurrent users (default: {DEFAULT_CONCURRENCY})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.users < 1:
        print("Error: --users must be at least 1", file=sys.stderr)
        return 1
    if args.concurrency < 1:
        print("Error: --concurrency must be at least 1", file=sys.stderr)
        return 1
    if args.concurrency > args.users:
        print("Warning: concurrency > users; using users as concurrency limit")
        args.concurrency = args.users

    print(f"Checking server at {args.base_url} ...")
    if not check_server(args.base_url):
        print(
            "Error: Cannot reach the app. Start it with: .\\venv\\Scripts\\python app.py",
            file=sys.stderr,
        )
        return 1

    collector = MetricsCollector()
    print(
        f"Running {args.users} users with {args.concurrency} concurrent workers ..."
    )

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(simulate_user, user_id, args.base_url, collector)
            for user_id in range(1, args.users + 1)
        ]
        for future in as_completed(futures):
            future.result()
    collector.report.wall_time_sec = time.perf_counter() - start

    print_report(collector.report, args.users, args.concurrency)

    if collector.report.users_failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
