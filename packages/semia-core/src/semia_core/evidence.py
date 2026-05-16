# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
"""Deterministic evidence-text alignment to prepared semantic units."""

from __future__ import annotations

import os
import re

from .artifacts import EvidenceAlignment, EvidenceAlignmentResult, Fact, PrepareBundle, SemanticUnit
from .facts import parse_facts

# Token regex covers:
#   - ASCII word runs (Latin letters, digits, underscore)
#   - Each CJK Unified Ideograph (Han) as its own token
#   - Each Hiragana / Katakana character
#   - Each Hangul syllable
# CJK scripts don't use whitespace, so character-level tokens give a meaningful
# Jaccard/containment basis without needing a real word segmenter.
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+" r"|[一-鿿]" r"|[぀-ゟ]" r"|[゠-ヿ]" r"|[가-힯]")

DEFAULT_EVIDENCE_THRESHOLD = 0.2


def _env_threshold() -> float:
    raw = os.environ.get("SEMIA_EVIDENCE_THRESHOLD")
    if raw is None:
        return DEFAULT_EVIDENCE_THRESHOLD
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_EVIDENCE_THRESHOLD
    return max(0.0, min(1.0, value))


def align_evidence_text(
    program_or_source,
    prepared: PrepareBundle | list[SemanticUnit] | tuple[SemanticUnit, ...],
    *,
    threshold: float | None = None,
) -> EvidenceAlignmentResult:
    """Align raw ``*_evidence_text`` rows to the best prepared evidence unit."""

    program = (
        parse_facts(program_or_source) if isinstance(program_or_source, str) else program_or_source
    )
    units = prepared.semantic_units if isinstance(prepared, PrepareBundle) else tuple(prepared)
    base_threshold = threshold if threshold is not None else _env_threshold()
    alignments: list[EvidenceAlignment] = []
    normalized: list[Fact] = []
    matched_unit_ids: set[int] = set()

    for fact in program.evidence_text_facts:
        evidence_text = fact.args[-1] if fact.args else ""
        unit, score = _best_unit(evidence_text, units)
        effective_threshold = _effective_threshold(base_threshold, evidence_text, unit)
        matched = bool(unit and score >= effective_threshold)
        alignment = EvidenceAlignment(
            fact=fact,
            evidence_text=evidence_text,
            evidence_id=unit.evidence_id if matched and unit else None,
            score=score,
            matched=matched,
            unit_id=unit.id if matched and unit else None,
        )
        alignments.append(alignment)
        normalized_fact = alignment.normalized_fact()
        if normalized_fact is not None:
            normalized.append(normalized_fact)
            if alignment.unit_id is not None:
                matched_unit_ids.add(alignment.unit_id)

    match_rate = (
        (len([a for a in alignments if a.matched]) / len(alignments)) if alignments else 0.0
    )
    total_tokens = sum(max(1, len(_tokens(unit.text))) for unit in units)
    covered_tokens = sum(
        max(1, len(_tokens(unit.text))) for unit in units if unit.id in matched_unit_ids
    )
    reference_coverage = (covered_tokens / total_tokens) if total_tokens else 0.0
    grounding_score = match_rate * reference_coverage
    return EvidenceAlignmentResult(
        alignments=tuple(alignments),
        normalized_facts=tuple(normalized),
        evidence_match_rate=match_rate,
        reference_unit_coverage=reference_coverage,
        grounding_score=grounding_score,
    )


def _best_unit(text: str, units: tuple[SemanticUnit, ...]) -> tuple[SemanticUnit | None, float]:
    if not units:
        return None, 0.0
    scored = [(unit, _score(text, unit.text)) for unit in units]
    return max(scored, key=lambda item: (item[1], -item[0].id))


def _score(evidence_text: str, unit_text: str) -> float:
    ev = evidence_text.strip().lower()
    unit = unit_text.strip().lower()
    if not ev or not unit:
        return 0.0
    ev_tokens = set(_tokens(ev))
    unit_tokens = set(_tokens(unit))
    if not ev_tokens or not unit_tokens:
        return 0.0

    shorter_chars = min(len(ev), len(unit))
    if (
        (ev in unit or unit in ev)
        and shorter_chars >= 8
        and min(len(ev_tokens), len(unit_tokens)) >= 2
    ):
        shorter = min(len(_tokens(ev)), len(_tokens(unit)))
        longer = max(len(_tokens(ev)), len(_tokens(unit)))
        return 1.0 if shorter == longer else max(0.75, shorter / max(1, longer))

    intersect = len(ev_tokens & unit_tokens)
    union = len(ev_tokens | unit_tokens)
    jaccard = intersect / union if union else 0.0

    # Containment from the evidence side. A short quote almost-entirely contained
    # in a long unit gets penalized by Jaccard (denominator blown up by unit size).
    # Cap at 0.75 so the substring path still wins for full-text matches.
    if len(ev_tokens) >= 3:
        containment = intersect / len(ev_tokens)
        if containment >= 0.5:
            return max(jaccard, containment * 0.75)

    return jaccard


def _effective_threshold(base: float, evidence_text: str, unit: SemanticUnit | None) -> float:
    """Relax the threshold when the unit is much longer than the evidence quote.

    A 5-token quote inside a 50-token paragraph has a Jaccard ceiling of
    ~0.10, well below the global 0.2 cutoff. Scale the threshold proportional
    to the size ratio so unbalanced pairs get a fair chance, but never drop
    below half the base threshold to keep small noise out.
    """

    if unit is None:
        return base
    ev_n = len(_tokens(evidence_text))
    unit_n = len(_tokens(unit.text))
    if ev_n == 0 or unit_n == 0 or ev_n >= unit_n:
        return base
    ratio = ev_n / unit_n
    return base * max(0.5, ratio)


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text)]
