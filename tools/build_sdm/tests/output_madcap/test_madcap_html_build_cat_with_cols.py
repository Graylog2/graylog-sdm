import pytest
from output_plugins.madcap_html_output import MadcapHtmlOutput

@pytest.fixture
def plugin():
    return MadcapHtmlOutput()

def test_build_category_data_with_columns_success(plugin):
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

    table_data = {
        '01': [
            {
                'gim_event_type_code': '010101',
                'gim_event_class': 'network',
                'gim_event_category': 'Network Activity',
                'gim_event_subcategory': 'Network Activity.Connections',
                'gim_event_type': 'Inbound Connection',
                'description': 'An inbound connection attempt was detected.'
            },
            {
                'gim_event_type_code': '010102',
                'gim_event_class': 'network',
                'gim_event_category': 'Network Activity',
                'gim_event_subcategory': 'Network Activity.Connections',
                'gim_event_type': 'Outbound Connection',
                'description': 'An outbound connection was attempted.'
            }
        ],
        '02': [
            {
                'gim_event_type_code': '010201',
                'gim_event_class': 'network',
                'gim_event_category': 'Network Activity',
                'gim_event_subcategory': 'Network Activity.Ports',
                'gim_event_type': 'Port Scan',
                'description': 'A port scan was detected.'
            }
        ]
    }

    result = plugin._build_category_data_with_columns(sample_input, table_data)

    assert '01' in result['subcategories']
    assert '02' in result['subcategories']
    assert result['subcategories']['01']['table_rows'] == table_data['01']
    assert result['subcategories']['02']['table_rows'] == table_data['02']


def test_build_category_data_with_columns_extra_table_key_ignored(plugin, caplog):
    category_input = {
        'name': 'Security',
        'code': '02',
        'class': 'security',
        'subcategories': {
            '01': {'name': 'Logins'}
        }
    }

    table_data = {
        '01': [{'gim_event_type_code': '020101', 'description': 'User login'}],
        '99': [{'gim_event_type_code': '999999', 'description': 'Invalid subcat'}]  # invalid subcategory
    }

    with caplog.at_level('WARNING'):
        result = plugin._build_category_data_with_columns(category_input, table_data)

    assert '01' in result['subcategories']
    assert result['subcategories']['01']['table_rows'] == table_data['01']
    assert '99' not in result['subcategories']

    # Optional: Confirm warning message was emitted
    warning_msgs = [record.message for record in caplog.records]
    assert any('Table data exists for code 99' in msg for msg in warning_msgs)
