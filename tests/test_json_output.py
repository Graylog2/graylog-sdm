import json
import logging
import sys
import tempfile
from pathlib import Path
from build_sdm.output_plugins.json_file_output import JsonFileOutput, JsonFileOutputConfig

def test_json_output_generates_file_correctly():
    '''Should generate JSON that can be parsed and matches the source data'''
    # Sample input data
    sample_config = {
        'example_key': 'example_value'
    }

    # Plugin config
    plugin_config = JsonFileOutputConfig(
        output_filename='test_output.json',
        json_indent=2
    )

    # Set up plugin
    plugin = JsonFileOutput()
    plugin.logger.setLevel(logging.CRITICAL)

    # Use a temp dir for output so the test is isolated
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir)
        plugin.generate(sample_config, output_path, plugin_config)

        # Check file exists
        output_file = output_path / plugin_config.output_filename
        assert output_file.exists(), 'Expected output file does not exist.'

        # Check file contents
        with output_file.open('r', encoding='utf-8') as f:
            contents = json.load(f)

        assert contents == sample_config, 'Output file contents did not match expected config.'
