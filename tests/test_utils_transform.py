"""Tests for restructure_gim_config."""

import pytest

from build_sdm.utils.transform import restructure_gim_config


def test_restructure_groups_categories_by_type() -> None:
    """Categories from separate files are grouped under their type."""
    gim_config = {
        "10.authentication.toml": {"type": "gim", "authentication": {"code": 10}},
        "12.network.toml": {"type": "gim", "network": {"code": 12}},
    }

    result = restructure_gim_config(gim_config)

    assert result == {"gim": {"authentication": {"code": 10}, "network": {"code": 12}}}


def test_restructure_rejects_duplicate_type_and_category() -> None:
    """Two files defining the same (type, category) pair raise instead of overwriting."""
    gim_config = {
        "12.network.toml": {"type": "gim", "network": {"code": 12}},
        "99.network_copy.toml": {"type": "gim", "network": {"code": 99}},
    }

    with pytest.raises(ValueError, match='Collision: type="gim" already contains category="network"'):
        restructure_gim_config(gim_config)


def test_restructure_allows_same_name_under_different_types() -> None:
    """The same category name under different types is not a collision."""
    gim_config = {
        "12.network.toml": {"type": "gim", "network": {"code": 12}},
        "network.toml": {"type": "field_schema", "network": {"entity_type": "top"}},
    }

    result = restructure_gim_config(gim_config)

    assert result["gim"]["network"] == {"code": 12}
    assert result["field_schema"]["network"] == {"entity_type": "top"}
