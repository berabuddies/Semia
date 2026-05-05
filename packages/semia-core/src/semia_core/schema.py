"""SDL schema constants used by parser, checker, and rules tooling."""

from __future__ import annotations

CORE_SCHEMA: dict[str, int] = {
    "skill": 1,
    "skill_doc_claim": 2,
    "action": 2,
    "action_trigger": 2,
    "action_gate": 2,
    "action_param": 3,
    "call": 2,
    "call_effect": 2,
    "call_code": 2,
    "call_action": 2,
    "call_action_arg": 3,
    "call_unconditional": 2,
    "call_conditional": 3,
    "call_region": 2,
    "call_input": 2,
    "call_output": 2,
    "call_region_untrusted": 1,
    "call_region_sensitive": 1,
    "call_region_secret": 1,
    "value": 3,
    "value_sensitive_allowed_action": 2,
    "value_secret_allowed_action": 2,
}

EVIDENCE_UNIT_SCHEMA: dict[str, int] = {
    "evidence_unit": 2,
}

_ENTITY_EVIDENCE_ARITIES: dict[str, int] = {
    "skill": 2,
    "action": 2,
    "call": 2,
    "value": 3,
}

EVIDENCE_TEXT_SCHEMA: dict[str, int] = {
    f"{relation}_evidence_text": _ENTITY_EVIDENCE_ARITIES.get(relation, arity + 1)
    for relation, arity in CORE_SCHEMA.items()
}

EVIDENCE_SCHEMA: dict[str, int] = {
    f"{relation}_evidence": _ENTITY_EVIDENCE_ARITIES.get(relation, arity + 1)
    for relation, arity in CORE_SCHEMA.items()
}

KNOWN_FACT_SCHEMA: dict[str, int] = {
    **CORE_SCHEMA,
    **EVIDENCE_UNIT_SCHEMA,
    **EVIDENCE_TEXT_SCHEMA,
    **EVIDENCE_SCHEMA,
}

ALLOWED_EFFECTS: frozenset[str] = frozenset(
    {
        "action_call",
        "agent_call",
        "chain_write",
        "code_eval",
        "crypto_sign",
        "db_read",
        "db_write",
        "env_read",
        "env_write",
        "fs_list",
        "fs_read",
        "fs_write",
        "net_read",
        "net_write",
        "proc_exec",
        "stdout",
    }
)

ALLOWED_TRIGGERS: frozenset[str] = frozenset(
    {
        "external",
        "llm",
        "on_import",
        "on_install",
    }
)

ALLOWED_GATES: frozenset[str] = frozenset(
    {
        "allowlist",
        "budget_limit",
        "confirmation_prompt",
        "credential_bound",
        "human_approval",
    }
)

ALLOWED_DOC_CLAIMS: frozenset[str] = frozenset(
    {
        "credential_bound",
        "local_only",
        "no_fs_write",
        "no_network",
        "read_only",
    }
)

ALLOWED_VALUE_KINDS: frozenset[str] = frozenset(
    {
        "derived",
        "literal",
        "local",
        "param",
        "secret",
        "sensitive_local",
        "untrusted",
    }
)

ALLOWED_CALL_CODES: frozenset[str] = frozenset(
    {
        "encoded_binary",
        "inline_code",
        "obfuscated",
        "script",
        "shell",
        "unresolved_target",
    }
)
