import logging

import pytest
from jinja2 import TemplateNotFound
from sys import path
from jinja2 import Environment, DictLoader, Template
from build_sdm.output_plugins.madcap_html_output import MadcapHtmlOutput

def test_load_template_success():
    '''Should successfully load and render a template from memory'''
    plugin = MadcapHtmlOutput()
    plugin._env = Environment(loader=DictLoader({'test.j2': 'Hello, {{ name }}!'}))
    plugin.logger.setLevel(logging.CRITICAL)

    template = plugin._load_template('test.j2', 'demo_category')
    assert isinstance(template, Template)
    rendered = template.render(name='Mike')

    assert rendered == 'Hello, Mike!'

def test_load_template_missing():
    '''Should log and re-raise TemplateNotFound if template is not found (plugin failures are fatal)'''
    plugin = MadcapHtmlOutput()
    plugin._env = Environment(loader=DictLoader({}))  # Empty template store
    plugin.logger.setLevel(logging.CRITICAL)

    with pytest.raises(TemplateNotFound):
        plugin._load_template('missing.j2', 'demo_category')
