import re
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Literal
from .plugin_config_schema import PluginConfigContainer

# Some additional check examples:
#    threshold: Optional[int] = Field(None, ge=0, le=100)
#    label: Optional[str] = Field(None, min_length=3, max_length=12)
#    network_transport: Literal['tcp', 'udp', 'icmp']
#      -> requires "from typing import Literal"
#    event_id: str = Field(..., regex=r'^EVT-\d{4}$')
#    max_retries: int = Field(..., ge=0, le=10, description="Retries must be between 0–10")
# For required fields, use Field with the ellipses - e.g., Field(..., {other stuff})

# NOTE that for optional fields, the following should be used:
# event_id: Optional[str] = Field(None, regex=r'^EVT-\d{4}$')
# network_transport: Optional[Literal['tcp', 'udp', 'icmp']] = None

class CategoryMeta(BaseModel):
    '''
    The meta property in the GIM config files can be used to provide
    configuration settings to specific plugins related to the GIM
    configuration items.
    '''
    plugin_config: Optional[PluginConfigContainer] = None

class SummaryTemplate(BaseModel):
    template_id: str
    title: str
    description: str
    summary: str

class IndicatorTemplate(BaseModel):
    type: str
    title: str
    description: str
    indicator: str
    danger: List[str] = []
    success: List[str] = []
    info: List[str] = []
    warning: List[str] = []
    primary: List[str] = []
    default: List[str] = []
    default_indicator: Optional[
        Literal[
            'info', 'danger', 'success', 'warning', 'primary'
            ]
        ] = 'info'


class SubcategoryEventType(BaseModel):
    name: str
    description: str

class Subcategory(BaseModel):
    '''
    Validate the subcategory object schema
    '''
    name: str
    description: str
    # NOTE: The word "class" is reserved, add an alias to the field
    # which can be applied when the object is serialized into a 
    # dictionary object, restoring the use of the word "class" in
    # the data provided to the output plugins.
    class_: Optional[str] = Field(None, alias='class')
    required_fields: List[str] = []
    recommended_fields: Optional[List[str]] = None
    optional_fields: List[str] = []
    summary: Optional[Dict[str, str]] = None
    event_type_codes: Dict[str, SubcategoryEventType]

    @validator('event_type_codes')
    def validate_event_type_code_keys(cls, value):
        '''
        Ensure the event type codes are string types containing two numeric digits.
        '''
        pattern = re.compile(r'^\d{2}$')
        for key in value:
            if not isinstance(key, str):
                raise TypeError(f'event_type_codes key {key!r} must be a string')
            if not pattern.match(key):
                raise ValueError(f'event_type_codes key {key!r} must be a 2-digit numeric string')
        return value

class GIMCategory(BaseModel):
    name: str
    code: str = Field(..., regex=r'^\d{2}$')
    description: str
    required_fields: List[str]
    recommended_fields: Optional[List[str]]
    optional_fields: Optional[List[str]]
    summaries: Optional[List[SummaryTemplate]] = []
    indicators: Optional[List[IndicatorTemplate]] = []
    subcategories: Dict[str, Subcategory]
    meta: Optional[CategoryMeta] = None

    @validator('subcategories')
    def validate_subcategory_keys(cls, value):
        '''
        Verify that the subcategory values are string type with two numeric digits
        '''
        pattern = re.compile(r'^\d{2}$')
        for key in value:
            if not isinstance(key, str):
                raise TypeError(f'subcategory key {key!r} must be a string')
            if not pattern.match(key):
                raise ValueError(f'subcategory key {key!r} must be a 2-digit numeric string')
        return value
