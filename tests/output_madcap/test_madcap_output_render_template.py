import logging

import pytest
from jinja2 import UndefinedError
from jinja2 import Environment, DictLoader, Template
from build_sdm.output_plugins.madcap_html_output import MadcapHtmlOutput


def test_render_template_success(caplog):
    '''
    Verify that _render_template successfully renders a valid template
    with the provided context and returns the expected HTML.
    '''
    plugin = MadcapHtmlOutput()
    plugin.logger.setLevel(logging.INFO)
    caplog.set_level(logging.ERROR)

    plugin._env = Environment(loader=DictLoader({'test.j2': 'Hello, {{ category }}!'}))
    template = plugin._env.get_template('test.j2')

    category = 'network'
    category_data = {'meta': {'description': 'network description'}}
    config = {'site_title': 'My GIM Docs'}

    result = plugin._render_template(template, category, category_data, config)

    assert result == 'Hello, network!'
    assert 'Failed to render template' not in caplog.text


def test_render_template_failure(caplog):
    '''
    Verify that _render_template notes the category on the error and re-raises
    when rendering fails due to a template logic error (e.g. undefined variable).
    '''
    plugin = MadcapHtmlOutput()
    plugin.logger.setLevel(logging.INFO)
    caplog.set_level(logging.ERROR)

    # This template references an undefined object attribute which causes rendering to fail
    plugin._env = Environment(loader=DictLoader({'broken.j2': '{{ category.upper_not_existing() }}'}))
    template = plugin._env.get_template('broken.j2')

    category = 'network'
    category_data = {}
    config = {}

    with pytest.raises(UndefinedError) as excinfo:
        plugin._render_template(template, category, category_data, config)

    assert f'rendering template for entry type [{category}]' in excinfo.value.__notes__
    assert caplog.text == ''
