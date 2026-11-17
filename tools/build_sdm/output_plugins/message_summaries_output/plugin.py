import json
import logging

from enum import Enum
from pathlib import Path
from pydantic import BaseModel, root_validator, ValidationError
from typing import Optional, List

from build_sdm.base_output import OutputPlugin
from build_sdm.utils.file import write_file

class IndicatorLevel(str, Enum):
    info = 'info'
    warning = 'warning'
    default = 'default'
    primary = 'primary'
    success = 'success'
    danger = 'danger'

class DuplicateTemplateIDError(ValueError):
    pass

class DuplicateIndicatorTemplateIDError(ValueError):
    pass
class MessageSummaryOutputConfig(BaseModel):
    output_filename: str = 'message_summaries.json'
    json_indent: int = 2
    enabled: bool = False

class SummaryTemplateModel(BaseModel):
    template_id: str
    summary: str
    title: str
    description: str

class IndicatorTemplateModel(BaseModel):
    default_indicator: IndicatorLevel
    indicator: str
    type: str
    title: str
    description: str
    success: list
    danger: list
    info: Optional[List[str]] = None
    primary: Optional[List[str]] = None
    warning: Optional[List[str]] = None
    default: Optional[List[str]] = None

class SummaryViewModel(BaseModel):
    title: str
    description: str
    summary_template: str
    indicator_template: Optional[str] = None
    default_indicator: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None

    @root_validator
    def check_mutual_exclusivity(cls, values):
        indicator = values.get('indicator_template')
        default = values.get('default_indicator')

        if (indicator is None and default is None) or (indicator and default):
            raise ValueError(
                'Exactly one of "indicator_template" or "default_indicator" must be defined'
            )
        return values


class MessageSummariesOutput(OutputPlugin[MessageSummaryOutputConfig]):
    ''''
    Generate a JSON-formatted message summary configuration data.
    '''
    def __init__(self):
        super().__init__()
        plugin_name = f'{self.__class__.__module__}.{self.__class__.__qualname__}'
        self.logger = logging.getLogger(plugin_name)

    enabled_by_default = True
    config_schema = MessageSummaryOutputConfig

    def build_summary_dict(self, gim_category: dict, summaries: Optional[dict] = None) -> dict:
        '''
        This will take a GIM category data and extract message summary configuration
        data from it and return it. It will accept a GIM category configuration
        dictionary object, and optionally a dictionary object that contains existing
        summary data. Any message summary configuration data that is found in the
        category data will be merged with the "summaries" data, if provided.

        Args:
            gim_category: The GIM category configuration dictionary
            summaries: Optional: Existing message summary config dictionary

        Returns:
            A dictionary containing the extracted message summary configuration data
        '''

# There are three elements that comprise the message summary configurations:
# - summary templates
# - indicator templates
# - summary views
#
# The next section will process all three types, which are stored in different
# sections of the GIM configuration data. The same approach will be applied to
# all three types:
# - Validate the element schema with the Pydantic summary template model
# - Validate ID values for the elements are unique
# - Add the validated configuration data to a combined dict for that element
#   type
#
# After that is completed all of the identified summary data dicts will be
# appended to the summary data dict which will be the return value.
        summary_templates = []
        summary_template_ids = set()
        indicator_templates = []
        indicator_template_ids = set()
        summary_views = []
        summary_view_ids = set()

        # Load existing object IDs if defined
        if summaries:
            if summaries['summaries'].get('summaryTemplate'):
                for summary_obj in summaries['summaries']['summaryTemplate']:
                    summary_template_ids.add(summary_obj['template_id'])
            if summaries['summaries'].get('indicatorTemplate'):
                for summary_obj in summaries['summaries']['indicatorTemplate']:
                    indicator_template_ids.add(summary_obj['type'])
            if summaries['summaries'].get('summaryView'):
                for summary_obj in summaries['summaries']['summaryView']:
                    summary_view_ids.add(summary_obj['title'])

        self.logger.debug('Building message summary configuration for category [%s]', gim_category['name'])

        for summary_config in gim_category.get('summaries'):
            self.logger.debug('Found summary template configuration in category %s', gim_category['name'])
            try:
                validated = SummaryTemplateModel(**summary_config)
                template_id = validated.template_id

                if template_id in summary_template_ids:
                    raise DuplicateTemplateIDError(
                        f'Duplicate summary template id [{template_id}] in category [{gim_category["name"]}]'
                    )

                summary_template_ids.add(template_id)
                summary_templates.append(validated.dict())
            except Exception as e:
                self.logger.warning(
                    'Invalid summary template in GIM category [%s]: %s', gim_category['name'], e
                    )
                raise

        for indicator_config in gim_category.get('indicators'):
            self.logger.debug('Found indicator template configuration in category %s', gim_category['name'])
            try:
                validated = IndicatorTemplateModel(**indicator_config)
                template_id = validated.type

                if template_id in indicator_template_ids:
                    raise DuplicateIndicatorTemplateIDError(
                        f'duplicate indicator template type {template_id} in category {gim_category["name"]}'
                    )

                indicator_template_ids.add(template_id)
                indicator_templates.append(validated.dict())
            except Exception as e:
                self.logger.warning(
                    'Invalid indicator template in GIM category [%s]: %s', gim_category['name'], e
                )
                raise

        for subcat_code in gim_category.get('subcategories'):
            if 'summary' in gim_category['subcategories'][subcat_code]:
                self.logger.debug(
                    'Found summary configuration in GIM category [%s.%s]',
                    gim_category['name'],gim_category['subcategories'][subcat_code]['name']
                    )
                try:
                    validated = SummaryViewModel(**gim_category['subcategories'][subcat_code]['summary'])
                    validated.category = gim_category['name']
                    validated.sub_category = gim_category['subcategories'][subcat_code]['name']
                    template_id = validated.title

                    if template_id in summary_view_ids:
                        raise DuplicateTemplateIDError(
                            f'duplicate summary view title {template_id} in category [{gim_category["name"]}]'
                        )

                    summary_view_ids.add(template_id)
                    summary_views.append(validated.dict())
                except Exception as e:
                    self.logger.warning(
                        'Invalid summary view in GIM category [%s.%s]',
                        gim_category['name'], gim_category['subcategories'][subcat_code]['name']
                    )
                    raise

        # Define the core message summary dict structure if it is not yet defined.
        if summaries is None:
            summaries = {'summaries': {'summaryTemplate': [], 'indicatorTemplate': [], 'summaryView': []}}

        # Add the summary elements
        summaries['summaries'].setdefault('summaryTemplate', []).extend(summary_templates)
        summaries['summaries'].setdefault('indicatorTemplate', []).extend(indicator_templates)
        summaries['summaries'].setdefault('summaryView', []).extend(summary_views)

        return summaries


    def generate(
            self,
            gim_config: dict,
            output_dir: Path,
            plugin_config: Optional[MessageSummaryOutputConfig] = None
            ) -> None:
        '''
        Build the Message Summaries JSON file that is used to configure Graylog
        Security Message Summaries.

        Args:
            gim_config: The full configuration dictionary loaded from TOML.
            output_dir: Where to write the output file.
            plugin_config: Optional validated configuration for this plugin.
        '''
        self.logger.info('Generating Message Summaries JSON output')

        if isinstance(plugin_config, MessageSummaryOutputConfig):
            self.logger.debug('Validated plugin config provided')
        else:
            self.logger.warning(
                'Plugin config is missing or invalid; using default values.'
                )
            plugin_config = MessageSummaryOutputConfig()

        summary_data = None

        # Build the summary template data
        for category in gim_config['gim']:
            summary_data = self.build_summary_dict(gim_config['gim'][category], summary_data)

        # Write the file output
        output_file = output_dir / plugin_config.output_filename
        try:
            write_file(output_file, json.dumps(summary_data, indent=plugin_config.json_indent))
        except OSError as e:
            self.logger.error('Unable to write [%s] due to write error %s', output_file, e)

        self.logger.debug('Plugin processing completed.')
