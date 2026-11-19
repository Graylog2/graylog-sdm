import json
import logging

from pathlib import Path
from pydantic import BaseModel
from typing import Optional

from build_sdm.base_output import OutputPlugin
from build_sdm.utils.file import write_file

class JsonFileOutputConfig(BaseModel):
    '''
    Validate the JsonFileOutput configuration settings with optional defaults
    '''
    output_filename: str = 'output.json'
    json_indent: int = 2
    enabled: bool = False

class JsonFileOutput(OutputPlugin[JsonFileOutputConfig]):
    ''''
    Generate a JSON-formatted file of the full contents of the loaded GIM data
    '''
    def __init__(self):
        super().__init__()
        plugin_name = f'{self.__class__.__module__}.{self.__class__.__qualname__}'
        self.logger = logging.getLogger(plugin_name)

    enabled_by_default = True
    config_schema = JsonFileOutputConfig

    def generate(self, gim_config: dict, output_dir: Path, plugin_config: Optional[JsonFileOutputConfig] = None) -> None:
        self.logger.info('Generating GIM configuration JSON output file')

        if isinstance(plugin_config, JsonFileOutputConfig):
            self.logger.info('Validated plugin config provided')
        else:
            self.logger.warning('Plugin config is missing or invalid; using default values.')
            plugin_config = JsonFileOutputConfig()

        output_file = output_dir / plugin_config.output_filename

        write_file(output_file, json.dumps(gim_config, indent=plugin_config.json_indent))

        self.logger.debug('Plugin processing completed.')
