"""Lint rules for SDM source data (build-sdm validate).

Each rule is a function that takes the loaded SdmModel and yields Violations. Rule IDs
are stable: they appear in output, in docs and in the base-ref comparison.
"""

from collections.abc import Callable, Iterable

from build_sdm.rules.fields import check_fields_exist, check_wildcards
from build_sdm.rules.gim import (
    check_codes,
    check_default_99,
    check_default_baseline,
    check_naming,
    check_unique_names,
)
from build_sdm.rules.meta import check_ascii_meta
from build_sdm.rules.model import SdmModel, Violation

__all__ = ["RULES", "Rule", "SdmModel", "Violation", "run_rules"]

Rule = Callable[[SdmModel], Iterable[Violation]]

RULES: dict[str, Rule] = {
    "naming": check_naming,
    "ascii-meta": check_ascii_meta,
    "unique-names": check_unique_names,
    "default-99": check_default_99,
    "default-baseline": check_default_baseline,
    "fields-exist": check_fields_exist,
    "wildcards": check_wildcards,
    "codes": check_codes,
}


def run_rules(model: SdmModel, rules: dict[str, Rule] | None = None) -> list[Violation]:
    """Run every rule against the model.

    Args:
        model: The loaded SDM source.
        rules: Rules to run; defaults to RULES.

    Returns:
        All violations, sorted by file, entry_key and rule_id.
    """
    violations = [v for rule in (rules or RULES).values() for v in rule(model)]
    return sorted(violations, key=lambda v: (v.file, v.entry_key, v.rule_id))
