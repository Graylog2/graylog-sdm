import pytest
from output_plugins.madcap_html_output import MadcapHtmlOutput

@pytest.fixture
def plugin():
    return MadcapHtmlOutput()

def test_build_subcat_tables_valid_input(plugin):
    sample_input = {
        'name': 'Network Activity',
        'code': '01',
        'class': 'network',
        'subcategories': {
            '01': {
                'name': 'Connections',
                'event_type_codes': {
                    '01': {
                        'name': 'Inbound Connection',
                        'description': 'An inbound connection attempt was detected.'
                    },
                    '02': {
                        'name': 'Outbound Connection',
                        'description': 'An outbound connection was attempted.'
                    }
                }
            },
            '02': {
                'name': 'Ports',
                'event_type_codes': {
                    '01': {
                        'name': 'Port Scan',
                        'description': 'A port scan was detected.'
                    }
                }
            }
        }
    }

    result = plugin._build_subcat_tables(sample_input)

    assert '01' in result
    assert '02' in result
    assert isinstance(result['01'], list)
    assert result['01'][0]['gim_event_type_code'] == '010101'
    assert result['01'][0]['gim_event_category'] == 'Network Activity'
    assert result['01'][0]['gim_event_subcategory'] == 'Network Activity.Connections'
    assert result['01'][0]['gim_event_type'] == 'Inbound Connection'
    assert result['01'][0]['gim_event_class'] == 'network'
    assert result['01'][0]['description'] == 'An inbound connection attempt was detected.'
    assert result['01'][1]['gim_event_type_code'] == '010102'
    assert result['01'][1]['gim_event_category'] == 'Network Activity'
    assert result['01'][1]['gim_event_subcategory'] == 'Network Activity.Connections'
    assert result['01'][1]['description'] == 'An outbound connection was attempted.'
    assert result['02'][0]['gim_event_type_code'] == '010201'
    assert result['02'][0]['gim_event_type'] == 'Port Scan'
    assert result['02'][0]['gim_event_subcategory'] == 'Network Activity.Ports'

def test_build_subcat_tables_missing_subcategories(plugin):
    sample_input = {
        'name': 'Authentication',
        'code': '02',
        'class': 'identity',
        # 'subcategories' intentionally omitted
    }

    result = plugin._build_subcat_tables(sample_input)
    assert result == {}

def test_build_subcat_tables_invalid_event_type_data(plugin):
    sample_input = {
        'name': 'System Events',
        'code': '03',
        'class': 'system',
        'subcategories': {
            '01': {
                'name': 'Reboots',
                'event_type_codes': {
                    '01': {
                        # 'name' key is missing
                        'description': 'System reboot detected.'
                    }
                }
            }
        }
    }

    # Should raise KeyError when 'name' is missing
    with pytest.raises(KeyError):
        plugin._build_subcat_tables(sample_input)
