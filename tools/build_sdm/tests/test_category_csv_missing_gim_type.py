import pytest
from output_plugins.category_data_csv_output import CategoryDataCSVOutput

@pytest.mark.parametrize("bad_config", [
    {},  # completely missing 'gim'
    {'gim': None},  # None instead of dict
    {'gim': 'not_a_dict'},  # wrong type
])
def test_missing_gim_key_or_invalid_type_raises(tmp_path, bad_config):
    plugin = CategoryDataCSVOutput()
    with pytest.raises(ValueError, match='Missing or invalid top-level "gim" key in gim_config; expected dictionary.'):
        plugin.generate(bad_config, tmp_path)
