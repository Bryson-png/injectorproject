"""
pers0na.py — Main runner for the persona-hijack harness.

Loops over (target × attack) pairs, sends each attack, judges the
response, and writes one JSONL trial per attack to runs/<run_id>/trials.jsonl
plus a runs/<run_id>/summary.json at the end.

Usage:
    python3 pers0na.py                        # All targets
    python3 pers0na.py --target code_review   # One target
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

from target import TARGETS
from attacks import get_attacks_for_scenario, ATTACKS
from judge import Judge


# Free-tier Gemini caps around 15 RPM on most models. 4 seconds between
# calls = 15 calls per minute, with a tiny safety margin.
API_DELAY_SECONDS = 4

TOOL_NAME = "pers0na"
TOOL_VERSION = "0.1.0"

# Outcome labels project-specific to pers0na. The triple is:
#   hijacked       — persona-hijack worked: rule was violated
#   held_persona   — target held its assigned persona / refused
#   error          — API or judge failure (excluded from rate denominator)
OUTCOME_HIJACKED = "hijacked"
OUTCOME_HELD = "held_persona"
OUTCOME_ERROR = "error"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_run_id() -> str:
    """A run_id that's filesystem-safe and sortable."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def open_run_dir(run_id: str) -> str:
    """Create runs/<run_id>/ and return the directory path."""
    run_dir = os.path.join("runs", run_id)
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def run_one_trial(
    run_id: str,
    target_key: str,
    attack: dict,
    judge: Judge,
) -> dict:
    """Send one attack, judge the result, return the trial dict."""
    target = TARGETS[target_key]

    response = target.send(attack["payload"])

    if response["error"]:
        return {
            "run_id": run_id,
            "tool": TOOL_NAME,
            "version": TOOL_VERSION,
            "timestamp": utc_now_iso(),
            "target": {
                "key": target_key,
                "name": target.name,
                "scenario": target.scenario,
                "model": target.model,
            },
            "attack": {
                "id": attack["id"],
                "name": attack["name"],
                "family": attack["family"],
                "payload": attack["payload"],
            },
            "response": {
                "text": response["text"],
                "error": True,
                "error_type": "target_error",
            },
            "judgment": {
                "attack_succeeded": False,
                "outcome": OUTCOME_ERROR,
                "confidence": "n/a",
                "reasoning": response["text"],
                "judge_error": False,
            },
        }

    time.sleep(API_DELAY_SECONDS)
    judgment = judge.evaluate(
        target_name=target.name,
        target_rules=target.system_prompt,
        attack_payload=attack["payload"],
        target_response=response["text"],
    )

    if judgment["judge_error"]:
        # The target call SUCCEEDED — it's the judge that failed. Keep
        # response.error=False so the JSONL accurately reflects which
        # subsystem broke. The trial still rolls up to outcome=error
        # because we couldn't grade it; the judge_error flag inside
        # judgment is the authoritative signal of which subsystem failed.
        outcome = OUTCOME_ERROR
        error_type = None
        response_error = False
    elif judgment["attack_succeeded"]:
        outcome = OUTCOME_HIJACKED
        error_type = None
        response_error = False
    else:
        outcome = OUTCOME_HELD
        error_type = None
        response_error = False

    return {
        "run_id": run_id,
        "tool": TOOL_NAME,
        "version": TOOL_VERSION,
        "timestamp": utc_now_iso(),
        "target": {
            "key": target_key,
            "name": target.name,
            "scenario": target.scenario,
            "model": target.model,
        },
        "attack": {
            "id": attack["id"],
            "name": attack["name"],
            "family": attack["family"],
            "payload": attack["payload"],
        },
        "response": {
            "text": response["text"],
            "error": response_error,
            "error_type": error_type,
        },
        "judgment": {
            "attack_succeeded": judgment["attack_succeeded"],
            "outcome": outcome,
            "confidence": judgment["confidence"],
            "reasoning": judgment["reasoning"],
            "judge_error": judgment["judge_error"],
        },
    }


def print_trial_trace(idx: int, n: int, trial: dict) -> None:
    """One-line trace line for the human watching the run."""
    name = trial["attack"]["name"]
    family = trial["attack"]["family"]
    outcome = trial["judgment"]["outcome"]
    confidence = trial["judgment"]["confidence"]
    response_len = len(trial["response"]["text"])
    label = {
        OUTCOME_HIJACKED: "HIJACKED",
        OUTCOME_HELD: "HELD",
        OUTCOME_ERROR: "ERROR",
    }[outcome]
    print(
        f"  [{idx}/{n}] {name} ({family}) — "
        f"{response_len:>5} chars → {label} ({confidence})"
    )


def print_summary(trials: list) -> None:
    """Aggregate counts grouped by target, then by attack family, then overall."""
    print("\n" + "=" * 60)
    print("SUMMARY REPORT")
    print("=" * 60)

    # Group by target
    targets = sorted(set(t["target"]["key"] for t in trials))
    grand_hijacked = grand_held = grand_error = 0

    for tk in targets:
        rows = [t for t in trials if t["target"]["key"] == tk]
        hijacked = sum(1 for r in rows if r["judgment"]["outcome"] == OUTCOME_HIJACKED)
        held = sum(1 for r in rows if r["judgment"]["outcome"] == OUTCOME_HELD)
        errors = sum(1 for r in rows if r["judgment"]["outcome"] == OUTCOME_ERROR)
        valid = hijacked + held
        pct = (hijacked / valid * 100) if valid > 0 else 0.0
        target_name = rows[0]["target"]["name"]
        model = rows[0]["target"]["model"]
        print(f"\n  {target_name} (model: {model}):")
        print(f"    Hijacked: {hijacked}/{valid} valid trials ({pct:.0f}%)")
        if errors:
            print(
                f"    Errors:   {errors} (API or judge failures — not counted as held)"
            )
        if hijacked:
            print("    Successful attacks:")
            for r in rows:
                if r["judgment"]["outcome"] == OUTCOME_HIJACKED:
                    print(
                        f"      - {r['attack']['name']} [{r['judgment']['confidence']} confidence]"
                    )
        grand_hijacked += hijacked
        grand_held += held
        grand_error += errors

    # By attack family
    print("\n  By attack family:")
    families = sorted(set(t["attack"]["family"] for t in trials))
    for fam in families:
        rows = [t for t in trials if t["attack"]["family"] == fam]
        hijacked = sum(1 for r in rows if r["judgment"]["outcome"] == OUTCOME_HIJACKED)
        valid = sum(1 for r in rows if r["judgment"]["outcome"] != OUTCOME_ERROR)
        pct = (hijacked / valid * 100) if valid > 0 else 0.0
        print(f"    {fam:25s}: {hijacked}/{valid} ({pct:.0f}%)")

    # Overall
    grand_valid = grand_hijacked + grand_held
    pct = (grand_hijacked / grand_valid * 100) if grand_valid > 0 else 0.0
    print(f"\n  OVERALL: {grand_hijacked}/{grand_valid} valid trials hijacked ({pct:.0f}%)")
    if grand_error:
        print(f"  ({grand_error} trial(s) excluded due to errors)")


def write_summary_file(run_dir: str, trials: list, judge_model: str) -> str:
    """Aggregate the trial outcomes into runs/<run_id>/summary.json.

    The summary file mirrors the on-screen SUMMARY REPORT: counts grouped
    by target, by attack family, plus an overall rollup. Keeping the JSON
    aligned with the printed report means downstream tools (the
    `dashb0rd` viewer in Phase 2) can render the same structure that a
    student reading the terminal already understands.
    """
    target_models = sorted(set(t["target"]["model"] for t in trials))

    def _empty_outcome_dict() -> dict:
        return {OUTCOME_HIJACKED: 0, OUTCOME_HELD: 0, OUTCOME_ERROR: 0}

    by_target: dict = {}
    by_family: dict = {}
    overall = _empty_outcome_dict()

    for t in trials:
        outcome_key = _outcome_to_summary_key(t["judgment"]["outcome"])
        tk = t["target"]["key"]
        fam = t["attack"]["family"]
        by_target.setdefault(tk, _empty_outcome_dict())[outcome_key] += 1
        by_family.setdefault(fam, _empty_outcome_dict())[outcome_key] += 1
        overall[outcome_key] += 1

    summary = {
        "tool": TOOL_NAME,
        "version": TOOL_VERSION,
        "run_started": trials[0]["timestamp"] if trials else utc_now_iso(),
        "run_ended": trials[-1]["timestamp"] if trials else utc_now_iso(),
        "target_models": target_models,
        "judge_model": judge_model,
        "trials_total": len(trials),
        "by_target": by_target,
        "by_family": by_family,
        "overall": overall,
    }
    path = os.path.join(run_dir, "summary.json")
    with open(path, "w") as f:
        json.dump(summary, f, indent=2)
    return path


def _outcome_to_summary_key(outcome: str) -> str:
    # Pass outcomes through unchanged so the summary.json keys match the
    # exact string literals used in trials.jsonl. Aggregating across runs
    # later is mechanical when the keys are stable.
    return outcome


def main() -> None:
    parser = argparse.ArgumentParser(
        description="pers0na — persona-hijack prompt-injection harness"
    )
    parser.add_argument(
        "--target",
        choices=list(TARGETS.keys()),
        help="Test a specific target (default: all)",
    )
    args = parser.parse_args()

    # Provider-neutral early check: either GOOGLE_API_KEY (Gemini path) or
    # OPENROUTER_API_KEY (Appendix A path) is sufficient. We don't check
    # which one matches the actual Target/Judge configuration — the lazy
    # init inside those classes raises the right error for the right key.
    if not (os.environ.get("GOOGLE_API_KEY") or os.environ.get("OPENROUTER_API_KEY")):
        print("ERROR: neither GOOGLE_API_KEY nor OPENROUTER_API_KEY is set.")
        print("Run: export GOOGLE_API_KEY='your-key-here'   # for the Gemini path")
        print(" or: export OPENROUTER_API_KEY='your-key-here'  # for the OpenRouter path")
        sys.exit(1)

    run_id = make_run_id()
    run_dir = open_run_dir(run_id)
    jsonl_path = os.path.join(run_dir, "trials.jsonl")

    print(f"{TOOL_NAME} v{TOOL_VERSION}  run_id={run_id}")
    print(f"Total attacks in library: {len(ATTACKS)}")
    print(f"Output: {jsonl_path}")

    judge = Judge()

    targets = [args.target] if args.target else list(TARGETS.keys())
    print(f"Targets: {', '.join(targets)}")

    trials: list = []
    with open(jsonl_path, "w") as f:
        for tk in targets:
            target = TARGETS[tk]
            attacks = get_attacks_for_scenario(target.scenario)
            print(f"\n{'=' * 60}")
            print(f"TARGET: {target.name}  ({len(attacks)} attacks)")
            print("=" * 60)
            for i, attack in enumerate(attacks, start=1):
                trial = run_one_trial(run_id, tk, attack, judge)
                f.write(json.dumps(trial) + "\n")
                f.flush()  # safe-by-default: every trial is durable on disk
                print_trial_trace(i, len(attacks), trial)
                trials.append(trial)
                time.sleep(API_DELAY_SECONDS)

    print_summary(trials)
    summary_path = write_summary_file(run_dir, trials, judge.model)
    print(f"\n  Per-trial transcripts: {jsonl_path}")
    print(f"  Aggregated summary:    {summary_path}")


if __name__ == "__main__":
    main()
