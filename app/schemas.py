from typing import Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypedDict


from typing import Optional
from pydantic import BaseModel

class ProductRequest(BaseModel):
    product_name: str = Field(..., description="Full commercial product name")
    raw_specs: str = Field(..., description="Technical specifications, dimensions, and materials")
    category_id: int = Field(..., description="WooCommerce category ID")
    price: str = Field(..., description="Retail price in AED")
    focus_keyphrase: str = Field(..., description="Primary focus keyphrase for SEO")
    image_url: Optional[str] = Field(None, description="Direct URL to product image")
    sku: Optional[str] = Field(None, description="Explicit SKU (if omitted, Gemini generates one)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_name": "Timer Faucet BPT-09 Self-Closing Basin Tap",
                "raw_specs": "Material: Solid Brass Construction with Polished Chrome Finish; Mechanism: Hydraulic Auto-Shutoff Cartridge; Timing: 7-12 seconds auto-close delay; Operating Pressure: 0.5 Bar to 6.0 Bar; Flow Rate: 3.0 L/min at 3 Bar; Inlet Connection: G 1/2 inch thread; Dimensions: Overall Height 140 mm, Spout Reach 110 mm, Mounting Hole 32-35 mm",
                "category_id": 121,
                "price": "145.00",
                "focus_keyphrase": "Self-Closing Timer Faucet",
                "image_url": "https://www.maat.ae/wp-content/uploads/timer-faucet-bpt09.jpg",
                "sku": "MAAT-BPT09-TAP"
            }
        }
    )
    

class ProductResponse(BaseModel):
    status: str
    wordpress_product_id: int
    wordpress_product_url: str
    generated_description: str
    sku: Optional[str] = None

    
class AgentState(TypedDict):
    """State dictionary passed through LangGraph nodes."""
    input_data: Dict[str, Any]
    generated_description: str
    validation_passed: bool
    validation_error: str
    wordpress_product_id: Optional[int]
    wordpress_product_url: Optional[str]