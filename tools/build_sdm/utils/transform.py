from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def restructure_gim_config(gim_config: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    '''
    Restructure the GIM config from file-oriented layout to type/category-oriented layout.

    Original: {filename: {'type': 'gim', 'network': {...}}}
    Output:   {'gim': {'network': {...}}}

    Raises:
        ValueError: if a (type, category) collision is detected.
    '''

    structured: Dict[str, Dict[str, Any]] = {}

    for filename, entry in gim_config.items():
        type_value = entry.get('type')
        if not type_value:
            raise ValueError(f'Missing "type" field in file: {filename}')

        # Extract category keys (everything except 'type')
        categories = {k: v for k, v in entry.items() if k != 'type'}

        if not categories:
            logger.warning('File %s contains no category data', filename)
            continue

        # Init if not present
        if type_value not in structured:
            structured[type_value] = {}

        for category_name, data in categories.items():
            if category_name in structured[type_value]:
                raise ValueError(f'Collision: type="{type_value}" already contains category="{category_name}"')

            structured[type_value][category_name] = data

    return structured
