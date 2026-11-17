import pytest
from pathlib import Path
from build_sdm.output_plugins.category_data_csv_output import CategoryDataCSVOutput, CategoryDataCSVOutputConfig

def test_missing_category_code_raises_value_error(tmp_path):
    plugin = CategoryDataCSVOutput()

    config = {
        'gim': {
            'authentication': {
                # 'code' is intentionally missing
                'name': 'Authentication',
                'subcategories': {
                    '01': {
                        'name': 'Login Attempts',
                        'class': 'access',
                        'event_type_codes': {
                            '00': {'name': 'Login Success'}
                        }
                    }
                }
            }
        }
    }

    with pytest.raises(ValueError, match=r'Missing "code" in category \[authentication\]'):
        plugin.generate(config, tmp_path)


def test_missing_top_level_name_raises_value_error(tmp_path):
    plugin = CategoryDataCSVOutput()

    # Prepare config missing 'name' at the top category level
    config = {
        'gim': {
            'authentication': {
                'code': '00',
                # 'name' is intentionally omitted
                'subcategories': {
                    '01': {
                        'name': 'Login Attempts',
                        'class': 'access',
                        'event_type_codes': {
                            '00': {'name': 'Login Success'},
                            '01': {'name': 'Login Failure'}
                        }
                    }
                }
            }
        }
    }

    plugin_config = CategoryDataCSVOutputConfig(output_filename='missing_name.csv')

    with pytest.raises(ValueError, match=r'Property "name" not defined.*'):
        plugin.generate(config, tmp_path, plugin_config)


def test_generate_raises_valueerror_if_category_name_missing(tmp_path: Path):
    plugin = CategoryDataCSVOutput()
    plugin_config = CategoryDataCSVOutputConfig(output_filename='output.csv')

    invalid_config = {
        'gim': {
            'authentication': {
                'code': '00',
                # 'name' field is intentionally omitted
                'subcategories': {
                    '01': {
                        'name': 'Login Attempts',
                        'event_type_codes': {
                            '00': {'name': 'Login Success'}
                        }
                    }
                }
            }
        }
    }

    with pytest.raises(ValueError, match='Property "name" not defined for category'):
        plugin.generate(invalid_config, tmp_path, plugin_config)
