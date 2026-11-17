from pydantic import BaseModel, Field, Extra

class PluginConfigContainer(BaseModel):
    class Config:
        extra = Extra.allow
