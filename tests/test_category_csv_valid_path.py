import pytest
from pathlib import Path
from build_sdm.output_plugins.category_data_csv_output import CategoryDataCSVOutput, CategoryDataCSVOutputConfig

def test_category_csv_output_happy_path(tmp_path):
    plugin = CategoryDataCSVOutput()

    # Prepare test config
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
                            '01': {'name': 'Login Failure'}
                        }
                    }
                }
            }
        }
    }

    plugin_config = CategoryDataCSVOutputConfig(output_filename='test_output.csv')

    plugin.generate(config, tmp_path, plugin_config)

    output_file = tmp_path / 'test_output.csv'
    assert output_file.exists()

    lines = output_file.read_text(encoding='utf-8').splitlines()
    assert len(lines) == 3
    assert lines[1].startswith('000100,')
    assert lines[2].startswith('000101,')
    assert '"gim_event_type_code","gim_category_data"' in lines[0]
    assert 'gim_event_type=Login Success' in lines[1]
    assert 'gim_event_class=access' in lines[1]
