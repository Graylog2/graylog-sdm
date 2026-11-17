import pytest

from jinja2 import TemplateNotFound
from pydantic import ValidationError
from pathlib import Path
from unittest.mock import MagicMock, patch
from copy import deepcopy

from build_sdm.output_plugins.madcap_html_output import MadcapHtmlOutput


# ----------------------------------------------------------------------
# FIXTURES
# ----------------------------------------------------------------------

@pytest.fixture
def mock_plugin() -> MadcapHtmlOutput:
    '''
    Fixture that returns a mocked MadcapHtmlOutput instance with stubbed dependencies.
    Ensures all attributes used by _generate_category_pages() return expected types.
    '''
    plugin = MadcapHtmlOutput()
    plugin.plugin_name = 'build_sdm.output_plugins.madcap_html_output.plugin.MadcapHtmlOutput'
    plugin._env = MagicMock()
    plugin.logger = MagicMock()

    # Patch internal helper methods to return simple valid types
    plugin._validate_category_plugin_config = MagicMock(
        return_value=MagicMock(category_template_filename='valid_template.j2')
    )
    plugin._load_template = MagicMock(return_value=MagicMock(render=MagicMock(return_value='<html>ok</html>')))
    plugin._render_template = MagicMock(return_value='<html>Rendered</html>')
    plugin._build_subcat_tables = MagicMock(return_value=['row1'])
    plugin._merge_field_lists = MagicMock(return_value=['field1'])
    plugin._build_category_data_with_columns = MagicMock(side_effect=lambda data, rows: data)

    return plugin


@pytest.fixture
def gim_config() -> callable:
    '''
    Fixture factory that returns a deep copy of a minimal valid GIM configuration.
    Each test receives its own isolated copy to prevent mutation side effects.
    '''
    base_cfg = {
        'config_output_plugin': {
            'plugin': {
                'build_sdm.output_plugins.madcap_html_output.plugin.MadcapHtmlOutput': {
                    'gim': {'html_output_subdir': 'gim'}
                }
            }
        },
        'gim': {
            'network': {
                'meta': {
                    'plugin_config': {
                        'build_sdm.output_plugins.madcap_html_output.plugin.MadcapHtmlOutput': {
                            'category_template_filename': 'example_template.j2'
                        }
                    }
                },
                'subcategories': {}
            },
            'identity': {
                'meta': {
                    'plugin_config': {
                        'build_sdm.output_plugins.madcap_html_output.plugin.MadcapHtmlOutput': {
                            'category_template_filename': 'example_template.j2'
                        }
                    }
                },
                'subcategories': {}
            },
        },
        'config': {}
    }

    def _factory() -> dict:
        return deepcopy(base_cfg)

    return _factory


# ----------------------------------------------------------------------
# SUCCESS CASE
# ----------------------------------------------------------------------

def test_generate_category_pages_success(
    tmp_path: Path,
    mock_plugin: MadcapHtmlOutput,
    gim_config: callable,
    monkeypatch: pytest.MonkeyPatch
) -> None:
    '''
    Should successfully load templates, render HTML, and write output files for each category.
    '''
    mock_template = MagicMock()
    mock_template.render.return_value = '<html>Rendered</html>'
    mock_plugin._env.get_template.return_value = mock_template

    cfg = gim_config()

    # Patch write_file to perform a real write for verification
    def fake_write_file(target_path: Path, content: str, overwrite: bool = True) -> None:
        target_path.write_text(content, encoding='utf-8')

    monkeypatch.setattr('build_sdm.output_plugins.madcap_html_output.plugin.write_file', fake_write_file)

    mock_plugin._generate_category_pages(cfg, tmp_path)

    output_dir = tmp_path / 'gim'
    expected_files = [output_dir / 'network.html', output_dir / 'identity.html']

    assert output_dir.is_dir()
    for file_path in expected_files:
        assert file_path.exists(), f'Expected output file not created: {file_path}'
        assert file_path.read_text().startswith('<html>')


# ----------------------------------------------------------------------
# FAILURE AND EDGE CASES
# ----------------------------------------------------------------------

def _written_pages(output_dir: Path) -> list[Path]:
    '''Return the HTML pages written under output_dir.'''
    return sorted(output_dir.rglob('*.html'))


def test_generate_category_pages_invalid_config_raises(
    tmp_path: Path,
    mock_plugin: MadcapHtmlOutput,
    gim_config: callable
) -> None:
    '''
    Should raise, without writing pages, if a category's plugin config is invalid (e.g., bad type).
    Plugin failures are fatal.
    '''
    del mock_plugin._validate_category_plugin_config  # use the real validator
    cfg = gim_config()
    cfg['gim']['network']['meta']['plugin_config']['build_sdm.output_plugins.madcap_html_output.plugin.MadcapHtmlOutput'][
        'category_template_filename'
    ] = 123  # invalid type

    with pytest.raises(ValidationError):
        mock_plugin._generate_category_pages(cfg, tmp_path)

    mock_plugin._env.get_template.assert_not_called()
    assert _written_pages(tmp_path) == []


def test_generate_category_pages_template_load_fails(
    tmp_path: Path,
    mock_plugin: MadcapHtmlOutput,
    gim_config: callable
) -> None:
    '''
    Should raise, without writing pages, if a category's template fails to load.
    '''
    del mock_plugin._load_template  # use the real loader against the mocked environment
    cfg = gim_config()
    mock_plugin._env.get_template.side_effect = TemplateNotFound('missing_template.j2')

    with pytest.raises(TemplateNotFound):
        mock_plugin._generate_category_pages(cfg, tmp_path)

    assert _written_pages(tmp_path) == []


def test_generate_category_pages_render_fails(
    tmp_path: Path,
    mock_plugin: MadcapHtmlOutput,
    gim_config: callable
) -> None:
    '''
    Should raise, without writing pages, if template rendering raises an exception.
    '''
    del mock_plugin._load_template
    del mock_plugin._render_template  # use the real loader and renderer
    mock_template = MagicMock()
    mock_template.render.side_effect = Exception('Render error')
    mock_plugin._env.get_template.return_value = mock_template

    cfg = gim_config()

    with pytest.raises(Exception, match='Render error'):
        mock_plugin._generate_category_pages(cfg, tmp_path)

    assert _written_pages(tmp_path) == []


def test_generate_category_pages_output_dir_creation_fails(
    mock_plugin: MadcapHtmlOutput,
    gim_config: callable
) -> None:
    '''
    Should raise RuntimeError if output directory creation fails.
    '''
    cfg = gim_config()
    cfg['config_output_plugin']['plugin']['build_sdm.output_plugins.madcap_html_output.plugin.MadcapHtmlOutput']['gim'][
        'html_output_subdir'
    ] = 'restricted'

    with patch('pathlib.Path.mkdir', side_effect=OSError('Permission denied')), \
         pytest.raises(RuntimeError) as exc_info:
        mock_plugin._generate_category_pages(cfg, Path('/root/forbidden'))

    assert 'Failed to create output directory' in str(exc_info.value)


def test_generate_category_pages_handles_write_errors(
    tmp_path: Path,
    mock_plugin: MadcapHtmlOutput,
    gim_config: callable,
    monkeypatch: pytest.MonkeyPatch
) -> None:
    '''
    Should log an error and re-raise if write_file raises OSError (plugin failures are fatal).
    '''
    cfg = gim_config()

    def exploding_write_file(*args, **kwargs):
        raise OSError('Disk full')

    monkeypatch.setattr('build_sdm.output_plugins.madcap_html_output.plugin.write_file', exploding_write_file)

    with pytest.raises(OSError, match='Disk full'):
        mock_plugin._generate_category_pages(cfg, tmp_path)
    mock_plugin.logger.error.assert_called()
