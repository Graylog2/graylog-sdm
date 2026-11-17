import pytest
from pathlib import Path
from build_sdm.output_plugins.category_data_csv_output import CategoryDataCSVOutput, CategoryDataCSVOutputConfig

def test_missing_event_type_codes_raises_runtime_error(tmp_path):
    plugin = CategoryDataCSVOutput()

    bad_config = {
        'gim': {
            'authentication': {
                'code': '00',
                'name': 'Authentication',
                'subcategories': {
                    '01': {
                        'name': 'Login Attempts',
                        'class': 'access',
                        # 'event_type_codes' key is missing entirely
                    }
                }
            }
        }
    }

    plugin_config = CategoryDataCSVOutputConfig(output_filename='bad.csv')

    with pytest.raises(RuntimeError, match=r'missing event_type_codes.*'):
        plugin.generate(bad_config, tmp_path, plugin_config)

    # Repeat with empty event_type_codes
    bad_config['gim']['authentication']['subcategories']['01']['event_type_codes'] = {}

    with pytest.raises(RuntimeError, match=r'missing event_type_codes.*'):
        plugin.generate(bad_config, tmp_path, plugin_config)


def test_missing_event_type_name_raises_value_error(tmp_path):
    plugin = CategoryDataCSVOutput()

    config = {
        'gim': {
            'authentication': {
                'code': '00',
                'name': 'Authentication',
                'subcategories': {
                    '01': {
                        'name': 'Login Attempts',
                        'class': 'access',
                        'event_type_codes': {
                            '00': {'name': 'Login Success'},
                            '01': {}  # Missing "name"
                        }
                    }
                }
            }
        }
    }

    plugin_config = CategoryDataCSVOutputConfig(output_filename='missing_type_name.csv')

    with pytest.raises(ValueError, match=r'.*missing a "name" property'):
        plugin.generate(config, tmp_path, plugin_config)


@pytest.mark.parametrize("bad_name", ["", None])
def test_empty_or_none_event_type_name_raises_runtime_error(tmp_path, bad_name):
    plugin = CategoryDataCSVOutput()

    config = {
        'gim': {
            'authentication': {
                'code': '00',
                'name': 'Authentication',
                'subcategories': {
                    '01': {
                        'name': 'Login Attempts',
                        'event_type_codes': {
                            '00': {'name': bad_name}
                        }
                    }
                }
            }
        }
    }

    plugin_config = CategoryDataCSVOutputConfig(output_filename='bad_name_test.csv')

    with pytest.raises(RuntimeError, match=r'has an empty or missing name property'):
        plugin.generate(config, tmp_path, plugin_config)


def test_missing_event_type_codes_raises_runtime_error(tmp_path):
    plugin = CategoryDataCSVOutput()

    config = {
        'gim': {
            'authentication': {
                'code': '00',
                'name': 'Authentication',
                'subcategories': {
                    '01': {
                        'name': 'Login Attempts',
                        # Missing 'event_type_codes'
                    }
                }
            }
        }
    }

    plugin_config = CategoryDataCSVOutputConfig(output_filename='missing_event_types.csv')

    with pytest.raises(RuntimeError, match=r'is missing event_type_codes or has no entries'):
        plugin.generate(config, tmp_path, plugin_config)


def test_generate_raises_valueerror_if_event_type_name_missing(tmp_path: Path):
    plugin = CategoryDataCSVOutput()
    plugin_config = CategoryDataCSVOutputConfig(output_filename='output.csv')

    invalid_config = {
        'gim': {
            'authentication': {
                'code': '00',
                'name': 'Authentication',
                'subcategories': {
                    '01': {
                        'name': 'Login Attempts',
                        'event_type_codes': {
                            '00': {}  # Missing 'name'
                        }
                    }
                }
            }
        }
    }

    with pytest.raises(ValueError, match=r'is missing a "name" property'):
        plugin.generate(invalid_config, tmp_path, plugin_config)
