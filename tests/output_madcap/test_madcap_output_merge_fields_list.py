import pytest
from build_sdm.output_plugins.madcap_html_output import MadcapHtmlOutput

@pytest.fixture
def plugin():
    return MadcapHtmlOutput()

def test_merge_field_lists_all_defined(plugin):
    category_input = {
        'required_fields': ['cat_field1', 'cat_field2'],
        'recommended_fields': ['cat_field3'],
        'optional_fields': ['cat_field4'],
        'subcategories': {
            '01': {
                'required_fields': ['sub_field1', 'cat_field2'],  # overlap on cat_field2
                'recommended_fields': ['sub_field3'],
                'optional_fields': ['sub_field4']
            }
        }
    }

    result = plugin._merge_field_lists(category_input, '01')

    assert sorted(result['required']) == ['cat_field1', 'cat_field2', 'sub_field1']
    assert sorted(result['recommended']) == ['cat_field3', 'sub_field3']
    assert sorted(result['optional']) == ['cat_field4', 'sub_field4']


def test_merge_field_lists_missing_category_fields(plugin):
    category_input = {
        # No required/recommended/optional at category level
        'subcategories': {
            '02': {
                'required_fields': ['only_sub_required'],
                'recommended_fields': [],
                'optional_fields': ['only_sub_optional']
            }
        }
    }

    result = plugin._merge_field_lists(category_input, '02')

    assert result['required'] == ['only_sub_required']
    assert result['recommended'] == []
    assert result['optional'] == ['only_sub_optional']


def test_merge_field_lists_missing_subcat_fields(plugin):
    category_input = {
        'required_fields': ['only_cat_required'],
        'recommended_fields': ['only_cat_recommended'],
        'optional_fields': [],
        'subcategories': {
            '03': {
                # Missing required/recommended/optional
            }
        }
    }

    result = plugin._merge_field_lists(category_input, '03')

    assert result['required'] == ['only_cat_required']
    assert result['recommended'] == ['only_cat_recommended']
    assert result['optional'] == []

def test_merge_field_lists_invalid_subcat_code(plugin):
    category_input = {
        'required_fields': ['cat_req'],
        'recommended_fields': [],
        'optional_fields': [],
        'subcategories': {
            '04': {
                'required_fields': ['sub_req']
            }
        }
    }

    # Should behave like missing subcat — return only category-level data
    result = plugin._merge_field_lists(category_input, 'nonexistent')

    assert result['required'] == ['cat_req']
    assert result['recommended'] == []
    assert result['optional'] == []
