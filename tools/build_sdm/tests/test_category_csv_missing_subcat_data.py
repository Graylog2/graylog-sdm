import pytest
from output_plugins.category_data_csv_output import CategoryDataCSVOutput, CategoryDataCSVOutputConfig

def test_missing_subcategory_name_raises_runtime_error(tmp_path):
    plugin = CategoryDataCSVOutput()

    gim_config = {
        'gim': {
            'access': {
                'code': '10',
                'name': 'Access Control',
                'subcategories': {
                    '01': {
                        # Missing 'name' key here
                        'class': 'access',
                        'event_type_codes': {
                            '00': {'name': 'Access Attempt'}
                        }
                    }
                }
            }
        }
    }

    plugin_config = CategoryDataCSVOutputConfig(output_filename='should_not_write.csv')

    with pytest.raises(RuntimeError) as exc_info:
        plugin.generate(gim_config, tmp_path, plugin_config)

    assert 'subcategory' in str(exc_info.value).lower()
    assert 'name' in str(exc_info.value).lower()
