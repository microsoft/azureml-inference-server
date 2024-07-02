from pydantic import BaseModel
from typing import List, Dict, Any

class GenericInputSchema(BaseModel):
    features: List[Dict[str, Any]]

class GenericOutputSchema(BaseModel):
    predictions: List[Dict[str, Any]]