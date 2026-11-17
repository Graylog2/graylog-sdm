import re
import pytest
from build_sdm.output_plugins.madcap_html_output import DocumentPostprocessor

@pytest.fixture
def default_postprocessor():
    return DocumentPostprocessor()

def test_lstrip_multiline_block_strips_leading_whitespace():
    input_html = '''<MadCap:codeSnippetBody>
        line 1
            line 2
      line 3
</MadCap:codeSnippetBody>'''
    expected = '''<MadCap:codeSnippetBody>
line 1
line 2
line 3</MadCap:codeSnippetBody>'''
    result = DocumentPostprocessor._lstrip_multiline_block(input_html)
    assert result == expected

def test_rstrip_ending_tags_removes_trailing_spaces():
    input_html = '<p>Test</p>   \n<p>Next</p>    \n'
    expected = '<p>Test</p>\n<p>Next</p>\n'
    result = DocumentPostprocessor._rstrip_ending_tags(input_html)
    assert result == expected

def test_remove_newlines_collapses_between_tags():
    input_html = '</div>\n\n\n<div>'
    expected = '</div>\n<div>'
    result = DocumentPostprocessor._remove_newlines(input_html)
    assert result == expected

def test_apply_docs_formatting_moves_td_closing_tag():
    input_html = '    <td class="field"><code class="val">x</code> </td>'
    expected = '    <td class="field"><code class="val">x</code>\n    </td>'
    result = DocumentPostprocessor._apply_docs_formatting(input_html)
    assert result == expected

def test_clean_runs_all_enabled(default_postprocessor):
    input_html = '''
<MadCap:codeSnippetBody>
    def func():
        pass
</MadCap:codeSnippetBody>


</div>

    <td class="field"><code class="val">x</code> </td>
    '''
    result = default_postprocessor.clean(input_html)

    # Should strip indentation inside code block
    assert '<MadCap:codeSnippetBody>\ndef func()' in result
    assert 'pass</MadCap:codeSnippetBody>' in result

    # Should collapse whitespace between tags
    assert '</div>' in result
    assert '<td class="field">' in result

    # Should reformat <td> with <code>
    assert '<code class="val">x</code>\n' in result
    assert '</td>' in result

def test_lstrip_multiline_block_skips_other_tags():
    input_html = '<div>\n    no change\n</div>'
    result = DocumentPostprocessor._lstrip_multiline_block(input_html)
    assert result == input_html
