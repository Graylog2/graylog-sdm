"""Write-failure propagation test for FieldMappingCSVOutput."""

from pathlib import Path
from unittest.mock import patch

import pytest

from build_sdm.output_plugins.field_mapping_csv_output import FieldMappingCSVOutput
from tests.gim_config_helpers import build_gim_config


def test_write_failure_propagates_instead_of_being_swallowed(tmp_path: Path) -> None:
    """An OSError from write_file must propagate, not be logged and swallowed.

    Swallowing it would let the build report success with no CSV written.
    """
    plugin = FieldMappingCSVOutput()

    gim_config = build_gim_config()

    with (
        patch(
            "build_sdm.output_plugins.field_mapping_csv_output.plugin.write_file",
            side_effect=OSError("disk full"),
        ),
        pytest.raises(OSError, match="disk full"),
    ):
        plugin.generate(gim_config, tmp_path)
