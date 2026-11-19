"""Builders for SdmModel instances in rule tests."""

from typing import Any

from build_sdm.rules import SdmModel
from tests.gim_config_helpers import build_gim_config

FILE = "src/sdm/infomodels/10.authentication.toml"


def model_from(gim_config: dict[str, Any]) -> SdmModel:
    """Wrap a gim_config from build_gim_config in an SdmModel, with every category in FILE.

    Args:
        gim_config: A gim_config with "gim" and "field_schema" sections.

    Returns:
        The model.
    """
    return SdmModel(
        gim=gim_config["gim"],
        field_schema=gim_config["field_schema"],
        category_files=dict.fromkeys(gim_config["gim"], FILE),
        entity_files={entity: f"src/sdm/schema/{entity}.toml" for entity in gim_config["field_schema"]},
    )


def add_subcategory(gim_config: dict[str, Any], code: str, name: str, **fields: Any) -> dict[str, Any]:
    """Add a subcategory to the single category in gim_config and return gim_config.

    Args:
        gim_config: A gim_config from build_gim_config.
        code: The new subcategory's code.
        name: The new subcategory's name.
        fields: Extra subcategory keys, e.g. required_fields.

    Returns:
        gim_config, modified in place.
    """
    category = next(iter(gim_config["gim"].values()))
    category["subcategories"][code] = {
        "name": name,
        "required_fields": [],
        "event_type_codes": {"00": {"name": f"{name}_event"}},
        **fields,
    }
    return gim_config


__all__ = ["FILE", "add_subcategory", "build_gim_config", "model_from"]
