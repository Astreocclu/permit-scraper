#!/usr/bin/env python3
"""
Benchmark Browser-Use with different LLM models.

Compares DeepSeek vs Claude models (Sonnet, Haiku, Opus) on permit scraping tasks.
Measures: success rate, time, estimated cost.

Usage:
    python3 scripts/benchmark_models.py --runs 10
    python3 scripts/benchmark_models.py --models deepseek sonnet haiku
    python3 scripts/benchmark_models.py --runs 3 --models haiku  # Quick test
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from services.browser_scraper.agent import PermitScraperAgent, MODEL_CONFIGS, ModelType
from services.browser_scraper.permit_tasks import get_task_for_city, CITY_TASKS

# Test cities - mix of platforms for variety
TEST_CITIES = [
    "southlake",      # EnerGov CSS
    "sachse",         # SmartGov
    "frisco",         # eTRAKiT
    "mckinney",       # EnerGov CSS
    "allen",          # EnerGov CSS
    "flower_mound",   # eTRAKiT
    "colleyville",    # EnerGov CSS
    "trophy_club",    # EnerGov CSS
    "prosper",        # eTRAKiT
    "keller",         # eTRAKiT
]


async def run_single_scrape(model: ModelType, city: str, run_num: int) -> Dict[str, Any]:
    """Run a single scrape and return results."""
    print(f"  [{run_num}] {model} -> {city}...", end=" ", flush=True)

    try:
        agent = PermitScraperAgent(headless=True, model=model)
        task = get_task_for_city(city, "2024-01-01", "2024-12-24")

        if not task:
            print("SKIP (no task)")
            return {"status": "skip", "reason": "no_task"}

        context = await agent.run_task(task, city)

        result = {
            "model": model,
            "city": city,
            "run": run_num,
            "success": context.is_successful or False,
            "done": context.is_done or False,
            "errors": context.errors or [],
            "actions_count": len(context.actions) if context.actions else 0,
            "elapsed_seconds": getattr(context, 'elapsed_seconds', 0),
            "final_result": str(context.final_result)[:200] if context.final_result else None,
        }

        status = "✓" if result["success"] else "✗"
        print(f"{status} ({result['elapsed_seconds']:.1f}s, {result['actions_count']} actions)")

        return result

    except Exception as e:
        print(f"ERROR: {e}")
        return {
            "model": model,
            "city": city,
            "run": run_num,
            "success": False,
            "error": str(e),
        }


async def benchmark_model(model: ModelType, num_runs: int) -> List[Dict[str, Any]]:
    """Run benchmark for a single model."""
    print(f"\n{'='*60}")
    print(f"BENCHMARKING: {model.upper()}")
    print(f"Model: {MODEL_CONFIGS[model]['model']}")
    print(f"Cost: ${MODEL_CONFIGS[model]['input_cost']}/1M in, ${MODEL_CONFIGS[model]['output_cost']}/1M out")
    print(f"{'='*60}")

    results = []
    for i in range(num_runs):
        city = TEST_CITIES[i % len(TEST_CITIES)]
        result = await run_single_scrape(model, city, i + 1)
        results.append(result)

        # Small delay between runs to avoid rate limits
        if i < num_runs - 1:
            await asyncio.sleep(2)

    return results


def analyze_results(all_results: Dict[str, List[Dict]]) -> Dict[str, Any]:
    """Analyze benchmark results."""
    analysis = {}

    for model, results in all_results.items():
        valid_results = [r for r in results if r.get("status") != "skip"]
        successful = [r for r in valid_results if r.get("success")]

        total_time = sum(r.get("elapsed_seconds", 0) for r in valid_results)
        avg_time = total_time / len(valid_results) if valid_results else 0

        # Estimate cost (rough - actual tokens not tracked yet)
        config = MODEL_CONFIGS[model]
        # Assume ~50k tokens per scrape (input + output)
        est_tokens = 50000 * len(valid_results)
        est_cost = (est_tokens / 1_000_000) * (config["input_cost"] + config["output_cost"])

        analysis[model] = {
            "total_runs": len(results),
            "valid_runs": len(valid_results),
            "successful": len(successful),
            "success_rate": len(successful) / len(valid_results) if valid_results else 0,
            "avg_time_seconds": avg_time,
            "total_time_seconds": total_time,
            "estimated_cost": est_cost,
            "cost_per_success": est_cost / len(successful) if successful else float('inf'),
        }

    return analysis


def print_summary(analysis: Dict[str, Any]):
    """Print summary comparison."""
    print("\n" + "="*80)
    print("BENCHMARK SUMMARY")
    print("="*80)

    # Header
    print(f"{'Model':<12} {'Success Rate':<14} {'Avg Time':<12} {'Est. Cost':<12} {'Cost/Success':<14}")
    print("-"*80)

    # Sort by success rate
    for model in sorted(analysis.keys(), key=lambda m: analysis[m]["success_rate"], reverse=True):
        stats = analysis[model]
        print(f"{model:<12} "
              f"{stats['success_rate']*100:>6.1f}% ({stats['successful']}/{stats['valid_runs']})  "
              f"{stats['avg_time_seconds']:>6.1f}s     "
              f"${stats['estimated_cost']:>6.4f}     "
              f"${stats['cost_per_success']:>6.4f}")

    print("="*80)

    # Recommendation
    best_value = min(analysis.keys(), key=lambda m: analysis[m]["cost_per_success"])
    best_quality = max(analysis.keys(), key=lambda m: analysis[m]["success_rate"])

    print(f"\nBest value (cost/success): {best_value}")
    print(f"Best quality (success rate): {best_quality}")


async def main():
    parser = argparse.ArgumentParser(description="Benchmark Browser-Use with different LLM models")
    parser.add_argument("--runs", type=int, default=10, help="Number of scrapes per model")
    parser.add_argument("--models", nargs="+", default=["deepseek", "sonnet", "haiku", "opus"],
                       choices=["deepseek", "sonnet", "haiku", "opus"],
                       help="Models to benchmark")
    parser.add_argument("--output", type=str, help="Output JSON file for results")
    args = parser.parse_args()

    print(f"Browser-Use LLM Benchmark")
    print(f"Runs per model: {args.runs}")
    print(f"Models: {', '.join(args.models)}")
    print(f"Test cities: {', '.join(TEST_CITIES[:args.runs])}")

    all_results = {}

    for model in args.models:
        try:
            results = await benchmark_model(model, args.runs)
            all_results[model] = results
        except Exception as e:
            print(f"ERROR benchmarking {model}: {e}")
            all_results[model] = [{"error": str(e)}]

    # Analyze
    analysis = analyze_results(all_results)
    print_summary(analysis)

    # Save results
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path("data/benchmark") / f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "config": {
                "runs_per_model": args.runs,
                "models": args.models,
                "test_cities": TEST_CITIES[:args.runs],
            },
            "results": all_results,
            "analysis": analysis,
        }, f, indent=2, default=str)

    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
