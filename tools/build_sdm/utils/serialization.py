from pydantic import BaseModel
from typing import Any

def to_serializable(obj: Any) -> Any:
    '''
    Recursively convert Pydantic models, dicts, and lists into pure Python structures
    that are JSON serializable.
    '''
    if isinstance(obj, BaseModel):
        #return obj.model_dump()  # Use .dict() if you're on Pydantic v1
        # exclude_none prevents keys defined with value None from being included
        # exclude_unset
        return obj.dict(by_alias=True, exclude_none=True, exclude_unset=False)
    elif isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_serializable(i) for i in obj]
    else:
        return obj
