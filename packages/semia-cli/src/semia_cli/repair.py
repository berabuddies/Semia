# SPDX-License-Identifier: Apache-2.0
"""Repair pipeline — LLM-mediated patch generation for flagged skills.


"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, TextIO

from semia_core.artifacts import Fact
from semia_core.facts import parse_facts
from semia_core.repair import (
    TracedFinding,
    apply_patch,
    build_evidence_map,
    build_repair_prompt,
    deduplicate_by_label,
    load_detection_rules,
    locate_in_source,
    parse_patch_response,
    trace_findings,
)

from . import core_adapter
from .llm_config import SynthesisConfig, SynthesisSettings, default_base_url, default_model, default_provider
from .llm_providers import call_provider


def repair(
    run_dir: Path,
    *,
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    trace_only: bool = False,
    stdout: TextIO | None = None,
) -> dict[str, Any]:
    """Run the repair pipeline on an existing scan run directory.

    Expects ``detection_result.json`` and ``synthesized_facts.dl`` to exist
    in *run_dir* (i.e. ``semia scan`` has already been run).

    Returns a summary dict with before/after finding counts and patch info.
    """
    import sys
    out = stdout or sys.stdout

    # ── Load scan artifacts ──
    det_path = run_dir / "detection_result.json"
    if not det_path.exists():
        raise FileNotFoundError(
            f"detection_result.json not found in {run_dir}; run `semia scan` first"
        )
    findings = json.loads(det_path.read_text()).get("findings", [])
    if not findings:
        print("No findings — nothing to repair.", file=out)
        return {"status": "clean", "findings": 0}

    norm = run_dir / "synthesized_facts_normalized.dl"
    facts_path = norm if norm.exists() else run_dir / "synthesized_facts.dl"
    raw_path = run_dir / "synthesized_facts.dl"

    core_facts = _load_core_facts(facts_path)
    evidence_map = build_evidence_map(raw_path.read_text())
    units = _load_units(run_dir)

    # ── Parse rules + trace ──
    rules = load_detection_rules()
    traced = trace_findings(findings, rules, core_facts, evidence_map)
    if units:
        locate_in_source(traced, units)
    unique = deduplicate_by_label(traced)

    print(f"{len(findings)} findings → {len(unique)} unique violation types", file=out)
    for tf in unique:
        count = sum(1 for f in findings if f["label"] == tf.label)
        print(f"  {tf.label} (x{count})", file=out)

    if trace_only:
        _print_trace(unique, out)
        return {"status": "traced", "findings": len(findings), "labels": len(unique)}

    # ── Read SKILL.md ──
    skill_md_path = _find_skill_md(run_dir)
    if not skill_md_path:
        raise FileNotFoundError("Cannot locate SKILL.md for patching")
    skill_md_content = skill_md_path.read_text()

    # ── Patch copy ──
    patched_dir = run_dir / "patched"
    if patched_dir.exists():
        shutil.rmtree(patched_dir)
    patched_dir.mkdir()
    (patched_dir / "SKILL.md").write_text(skill_md_content)

    # ── LLM config ──
    resolved_provider = default_provider(provider)
    resolved_model = default_model(model, resolved_provider)
    resolved_base_url = default_base_url(base_url, resolved_provider)
    config = SynthesisConfig(
        provider=resolved_provider,
        model=resolved_model,
        base_url=resolved_base_url,
    )
    settings = SynthesisSettings.from_env()

    # ── Generate + apply patches ──
    repairs: list[dict[str, Any]] = []
    current_skill_md = skill_md_content

    for tf in unique:
        count = sum(1 for f in findings if f["label"] == tf.label)
        print(f"\nRepairing: {tf.label} (x{count})", file=out)

        prompt = build_repair_prompt(tf, core_facts, evidence_map, current_skill_md)

        try:
            response = call_provider(run_dir, prompt, config, settings)
        except Exception as e:
            print(f"  LLM error: {e}", file=out)
            continue

        patch = parse_patch_response(response)
        if not patch:
            print("  Failed to parse LLM response", file=out)
            continue

        print(f"  Analysis: {patch.get('analysis', '?')[:150]}", file=out)
        print(f"  Strategy: {patch.get('fix_strategy', '?')}", file=out)

        applied = apply_patch(patch, patched_dir)
        for desc in applied:
            print(f"    {desc}", file=out)

        # Re-read for next iteration (patches accumulate)
        patched_md = patched_dir / "SKILL.md"
        if patched_md.exists():
            current_skill_md = patched_md.read_text()

        repairs.append({
            "label": tf.label,
            "analysis": patch.get("analysis", ""),
            "strategy": patch.get("fix_strategy", ""),
            "conjunct": patch.get("conjunct_to_break", ""),
            "applied": applied,
        })

    # ── Write outputs ──
    result_path = run_dir / "repair_result.json"
    result = {
        "status": "repaired",
        "findings": len(findings),
        "labels_repaired": len(repairs),
        "repairs": repairs,
        "patched_skill_md": str(patched_dir / "SKILL.md"),
    }
    result_path.write_text(json.dumps(result, indent=2) + "\n")
    print(f"\nRepair result: {result_path}", file=out)
    print(f"Patched SKILL.md: {patched_dir / 'SKILL.md'}", file=out)

    return result


def _load_core_facts(path: Path) -> list[Fact]:
    program = parse_facts(path.read_text())
    return list(program.core_facts)


def _load_units(run_dir: Path) -> list[dict[str, Any]] | None:
    units_path = run_dir / "prepare_units.json"
    if not units_path.exists():
        return None
    data = json.loads(units_path.read_text())
    return data.get("units")


def _find_skill_md(run_dir: Path) -> Path | None:
    """Locate the original SKILL.md from prepare metadata."""
    meta_path = run_dir / "prepare_metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        source = meta.get("source", {})
        root = source.get("root")
        if root:
            for name in ("SKILL.md", "skill.md"):
                p = Path(root) / name
                if p.exists():
                    return p
    # Fallback: look in prepared_skill.md
    prepared = run_dir / "prepared_skill.md"
    if prepared.exists():
        return prepared
    return None


def _print_trace(unique: list[TracedFinding], out: TextIO) -> None:
    """Pretty-print the trace results."""
    print("\nTrace results:", file=out)
    for tf in unique:
        print(f"\n  {tf.label}({', '.join(tf.fields[:3])})", file=out)
        print(f"  Rule: {tf.rule.head}", file=out)
        for conj in tf.conjuncts:
            neg = "¬ " if conj.is_negation else ""
            n = len(conj.matched_facts)
            print(f"    {neg}{conj.conjunct_template}  ({n} facts)", file=out)
            for loc in conj.source_locations[:2]:
                print(f"      @ {loc['file']}:{loc['line_start']}-{loc['line_end']}", file=out)