# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 berabuddies
"""Pure-Python Datalog evaluator for the Soufflé subset used by Semia rules.

Implements just enough of Soufflé's surface to run the SDL detector rules
without requiring the Soufflé binary: stratified negation, body disjunction,
recursion, the ``contains/2`` builtin, and tab-delimited CSV output.
"""

from .engine import EvalResult, run_evaluator
from .parser import ParseError, parse_dl_file

__all__ = ["EvalResult", "ParseError", "parse_dl_file", "run_evaluator"]
