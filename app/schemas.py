from typing import Dict, Any, Optional
from pydantic import BaseModel
from typing_extensions import TypedDict


class ProductRequest(BaseModel):
    """Schema for incoming POST requests to FastAPI."""
    product_name: str
    raw_specs: str
    category_id: int
    price: str
    image_url: Optional[str] = None
    focus_keyphrase: Optional[str] = None


class AgentState(TypedDict):
    """State dictionary passed through LangGraph nodes."""
    input_data: Dict[str, Any]
    generated_description: str
    validation_passed: bool
    validation_error: str
    wordpress_product_id: Optional[int]
    wordpress_product_url: Optional[str]