from enum import Enum
from pydantic import BaseModel, conlist, Field, StrictStr, validator
from typing import List, Literal, Dict, Optional, Any


class FieldSchemaField(BaseModel):
    '''
    One field of a field_schema entity. field_type is checked against
    config.field_schema_config.allowed_field_types after all files are loaded
    (gim_schema.field_types.validate_field_types), since that list lives in the
    SDM source rather than in code.
    '''
    field_suffix: StrictStr
    field_type: StrictStr
    description: StrictStr
    example_values: Optional[StrictStr] = None

class FieldSchemaEntity(BaseModel):
    '''
    Represents one entity's definition within a field_schema TOML file (e.g.
    "file", "hash", "reserved").

    entity_type controls how each field's full name is derived and, for "sub"
    entities, how they relate to other entities:
    - "top": fields are prefixed with the entity name, e.g. file_name.
    - "sub": fields are not standalone; applies_to names the "top" entities
      each field is appended to, e.g. hash's sha256 field becomes both
      file_hash_sha256 and process_hash_sha256 when applies_to = ["file", "process"].
    - "reserved": field_suffix values are already the literal field name,
      with no entity-name prefix.
    '''
    description: str
    title: Optional[str] = None
    entity_type: Literal['top', 'sub', 'reserved']
    fields: List[FieldSchemaField]
    applies_to: Optional[List[StrictStr]] = None
    meta: Optional[Dict[str, Any]] = None

    class Config:
        extra = 'forbid'

    @validator('applies_to', always=True)
    def validate_applies_to_matches_entity_type(cls, v, values):
        entity_type = values.get('entity_type')
        if entity_type == 'sub':
            if not v:
                raise ValueError(
                    'applies_to must be a non-empty list of parent entity names '
                    'when entity_type is "sub"'
                )
        elif v:
            raise ValueError(
                'applies_to is only allowed when entity_type is "sub"'
            )
        return v


class FieldSchemaDocument(BaseModel):
    '''
    Represents the full field_schema TOML file.
    Each top-level key is an entity name, mapping to its definition.
    '''
    type: Literal['field_schema']
    entities: Dict[str, FieldSchemaEntity]

    class Config:
        extra = 'forbid'

    @classmethod
    def parse_obj(cls, obj):
        # Transform raw TOML structure into {entities: {...}} format
        entity_keys = {k: v for k, v in obj.items() if k != 'type'}
        return super().parse_obj({
            'type': obj.get('type'),
            'entities': entity_keys
        })


class FieldSchemaConfigBody(BaseModel):
    '''
    Validate the field_schema_config branch entries. This will not validate the
    allowed_field_types value, as the value itself is to be used as a check to
    verify which mapping types are allowed to be defined in the schema.
    '''
    allowed_field_types: List[StrictStr]

    @validator('allowed_field_types')
    def ensure_not_empty_and_unique(cls, values):
        if not values:
            raise ValueError('allowed_field_types must not be empty')
        if len(values) != len(set(values)):
            raise ValueError('allowed_field_types contains duplicates')
        return values


class SectionType(str, Enum):
    PARAGRAPHS = 'paragraphs'
    LIST_UNORDERED = 'list_unordered'
    LIST_ORDERED = 'list_ordered'
    TABLE = 'table'
    HINT = 'hint'
    WARNING = 'warning'


class SectionDefinition(BaseModel):
    type: SectionType
    section_header: Optional[str] = None
    content: Any  # Validated below

    @validator('content')
    def validate_content_by_type(cls, v, values):
        section_type = values.get('type')
        if section_type is None:
            raise ValueError('Section type must be provided before validating content.')

        # Types that require a list of strings
        if section_type in {
            SectionType.PARAGRAPHS,
            SectionType.LIST_UNORDERED,
            SectionType.LIST_ORDERED,
            SectionType.TABLE
        }:
            if not isinstance(v, list) or not all(isinstance(item, str) for item in v):
                raise TypeError(f'Content for type "{section_type}" must be a list of strings.')
        # Types that require a single string
        elif section_type in {SectionType.HINT, SectionType.WARNING}:
            if not isinstance(v, str):
                raise TypeError(f'Content for type "{section_type}" must be a string.')
        else:
            raise ValueError(f'Unknown section type: {section_type}')

        return v


class ConfigExtendDocumentation(BaseModel):
    sections: List[SectionDefinition]


class ConfigDocument(BaseModel):
    '''
    Represents the field schema config data loaded from a config file with a
    configuration stanza, which is one of the following:
    - field_schema_config - associated with the schema field definitions
    - gim_config - associated with the Graylog Information Model config
    - sdm_version - the current SDM schema version, consumed by
      scripts/se_val.py to validate a message's sdm_version field for
      major-version compatibility
    '''
    type: Literal['config']
    field_schema_config: Optional[Dict[str, Any]] = None
    gim_config: Optional[Dict[str, Any]] = None
    sdm_version: Optional[Dict[str, Any]] = None
