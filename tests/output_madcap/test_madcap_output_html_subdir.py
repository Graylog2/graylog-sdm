"""Tests for html_output_subdir validation on the MadCap top-level section models."""

import pytest
from pydantic import ValidationError

from build_sdm.output_plugins.madcap_html_output.models import (
    TopLevelFieldSchemaSectionMetadata,
    TopLevelGimSectionMetadata,
)

SectionModel = type[TopLevelGimSectionMetadata] | type[TopLevelFieldSchemaSectionMetadata]

SECTION_MODELS: list[SectionModel] = [TopLevelGimSectionMetadata, TopLevelFieldSchemaSectionMetadata]

VALID_SUBDIRS = [
    "field_schema",
    "FIELD_SCHEMA_2024",
    "My_Dir123",
    "Graylog Information Models",
    "Field Schema Entities",
]

INVALID_SUBDIRS = [
    "../etc",
    "field/schema",
    "field-schema",
    "field.schema",
    "field@schema!",
    "",
]


@pytest.mark.parametrize("model", SECTION_MODELS)
@pytest.mark.parametrize("subdir", VALID_SUBDIRS)
def test_valid_subdir_is_accepted(model: SectionModel, subdir: str) -> None:
    """Letters, digits, underscores and spaces are accepted unchanged."""
    section = model(title="Title", intro="Intro", html_output_subdir=subdir)

    assert section.html_output_subdir == subdir


@pytest.mark.parametrize("model", SECTION_MODELS)
@pytest.mark.parametrize("subdir", INVALID_SUBDIRS)
def test_invalid_subdir_is_rejected(model: SectionModel, subdir: str) -> None:
    """Path separators, traversal, punctuation and empty names are rejected."""
    with pytest.raises(ValidationError):
        model(title="Title", intro="Intro", html_output_subdir=subdir)


@pytest.mark.parametrize("model", SECTION_MODELS)
def test_subdir_is_optional(model: SectionModel) -> None:
    """Omitting html_output_subdir leaves it unset."""
    section = model(title="Title", intro="Intro")

    assert section.html_output_subdir is None
