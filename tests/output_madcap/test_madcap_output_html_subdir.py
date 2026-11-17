from pydantic import BaseModel, Field, validator, ValidationError
from typing import Optional
import re


class OutputSubdirModel(BaseModel):
    html_output_subdir: Optional[str] = Field(default=None)

    @validator('html_output_subdir')
    @classmethod
    def validate_subdir(cls, value):
        if value is None:
            return value
        if not re.fullmatch(r'[A-Za-z0-9_]+', value):
            raise ValueError('Subdirectory names must contain only letters, digits, or underscores')
        return value


# Test cases
valid_values = [
    'field_schema',
    'FIELD_SCHEMA_2024',
    'My_Dir123',
    'gim_config',
    'Valid123'
]

invalid_values = [
    '../etc',
    'field/schema',
    'field schema',
    'field-schema',
    'field.schema',
    'field@schema!',
    ''
]

valid_results = []
invalid_results = []

for value in valid_values:
    try:
        OutputSubdirModel(html_output_subdir=value)
        valid_results.append((value, True))
    except ValidationError:
        valid_results.append((value, False))

for value in invalid_values:
    try:
        OutputSubdirModel(html_output_subdir=value)
        invalid_results.append((value, True))
    except ValidationError:
        invalid_results.append((value, False))

(valid_results, invalid_results)
