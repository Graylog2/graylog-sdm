import logging

from pathlib import Path
from pydantic import BaseModel
from typing import Optional, List

from build_sdm.base_output import OutputPlugin
from build_sdm.utils.file import write_file

class CategoryDataCSVOutputConfig(BaseModel):
    output_filename: str = 'category_data.csv'
    enabled: bool = False


class CategoryDataCSVOutput(OutputPlugin[CategoryDataCSVOutputConfig]):
    '''
    Generate the category data CSV file used by Illuminate core to enrich events with
    category data. This file should be copied in to the Illuminate Core directory
    'data'.
    '''
    def __init__(self):
        super().__init__()
        plugin_name = f'{self.__class__.__module__}.{self.__class__.__qualname__}'
        self.logger = logging.getLogger(plugin_name)

    enabled_by_default = True
    config_schema = CategoryDataCSVOutputConfig

    def generate(self, gim_config: dict, output_dir: Path, plugin_config: Optional[CategoryDataCSVOutputConfig] = None) -> None:
        self.logger.debug('Plugin initialized, generating Category Data CSV output')

        # Use the provided plugin_config if it was provided, or use the default settings
        if isinstance(plugin_config, CategoryDataCSVOutputConfig):
            self.logger.info('Validated plugin config provided')
        else:
            self.logger.warning('Plugin config is missing or invalid; using default values.')
            plugin_config = CategoryDataCSVOutputConfig()

        output_file = output_dir / plugin_config.output_filename

        lookup_data = [ '"gim_event_type_code","gim_category_data"' ]

        if 'gim' not in gim_config or not isinstance(gim_config['gim'], dict):
            error_msg = 'Missing or invalid top-level "gim" key in gim_config; expected dictionary.'
            raise ValueError(error_msg)

        for category in gim_config['gim']:
            self.logger.debug('Processing category [%s]', category)

            self.logger.debug('Found GIM category entry [%s]', category)
            cat_lines = self._build_lookup_lines(gim_config['gim'][category], category)

            if cat_lines:
                lookup_data.extend(cat_lines)
            else:
                error_msg = f'Unable to generate lookup data for category {category}'
                raise RuntimeError(error_msg)

        lookup_data.sort()

        write_file(output_file, '\n'.join(lookup_data))

        self.logger.info('Saved CSV to file %s', output_file)
        self.logger.debug('Plugin processing completed.')

    def _build_lookup_lines(self, gim_entry: dict, category: str) -> Optional[List[str]]:
        '''
        Generate CSV-formatted lookup line for a given category.

        Args:
            gim_entry: Dictionary object containing configuration for a GIM category
            category: String indicating the category being processed
        '''
        lookup_entry = []

        if 'code' not in gim_entry:
            error_msg = f'Missing "code" in category [{category}]'
            raise ValueError(error_msg)

        cat_code = gim_entry['code']

        for subcat_code in gim_entry['subcategories']:
            self.logger.debug(
                'Loading category [%s] subcategory code [%s]',
                category, subcat_code
                )
            subcat = gim_entry['subcategories'][subcat_code]

            if 'name' not in subcat:
                error_msg = f'Subcategory [{subcat_code}] under category [{category}] is missing a "name" field.'
                raise RuntimeError(error_msg)

            subcat_name = subcat['name']

            # Validate event_type_codes presence and non-empty
            if 'event_type_codes' not in subcat or not subcat['event_type_codes']:
                error_msg = (
                    f'Subcategory [{subcat_code}] under category [{category}] '
                    'is missing event_type_codes or has no entries.'
                )
                raise RuntimeError(error_msg)

            # Define the category name
            if 'name' not in gim_entry:
                error_msg = f'Property "name" not defined for category [{category}]'
                raise ValueError(error_msg)

            category_name = gim_entry['name']
            self.logger.debug('Processing category name [%s]', category_name)

            for type_code in subcat['event_type_codes']:
                if 'name' not in subcat['event_type_codes'][type_code]:
                    error_msg = (
                        f'GIM event category [{category}] '
                        f'type [{cat_code}{subcat_code}{type_code}] is missing a "name" property'
                    )
                    raise ValueError(error_msg)

                event_type_info = subcat['event_type_codes'][type_code]
                event_type_name = event_type_info.get('name')

                if not event_type_name:
                    error_msg = (
                        f'GIM event category [{category}] type [{cat_code}{subcat_code}{type_code}] '
                        'has an empty or missing name property.'
                    )
                    raise RuntimeError(error_msg)

                # Build the category map lookup entries - if there is a class defined,
                # include it
                line = None
                if 'class' in subcat:
                    entry_class = subcat['class']
                    line = f'{cat_code}{subcat_code}{type_code},' \
                        f'"gim_event_class={entry_class},' \
                        f'gim_event_category={category_name},' \
                        f'gim_event_subcategory={category_name}.{subcat_name},' \
                        f'gim_event_type={event_type_name}"'
                else:
                    line = f'{cat_code}{subcat_code}{type_code},' \
                        f'"gim_event_category={category_name},' \
                        f'gim_event_subcategory={category_name}.{subcat_name},' \
                        f'gim_event_type={event_type_name}"'

                if line:
                    self.logger.debug(
                        'Cat code [%s], Subcat code [%s], Type code [%s]',
                        cat_code, subcat_code, type_code
                        )
                    self.logger.debug('Adding line [%s]', line)
                    lookup_entry.append(line)

        return lookup_entry
