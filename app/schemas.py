from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypedDict


class ProductRequest(BaseModel):
    product_name: str = Field(..., description="Full commercial product name")
    raw_specs: str = Field(..., description="Technical specifications, dimensions, and materials")
    category_id: int = Field(..., description="Primary WooCommerce category ID")
    additional_category_ids: Optional[List[int]] = Field(None, description="Extra WooCommerce category IDs to tag alongside category_id (e.g. a parent category)")
    price: Optional[str] = Field(None, description="Retail price in AED. Omit for enquiry-only listings (no price shown, e.g. B2B catalog items)")
    focus_keyphrase: str = Field(..., description="Primary focus keyphrase for SEO")
    image_url: Optional[str] = Field(None, description="Direct URL to an already-hosted product image")
    image_paths: Optional[List[str]] = Field(None, description="Local file paths to upload to the WordPress media library before publishing. First path becomes the primary product image; the rest become gallery images. Takes priority over image_url if both are given.")
    sku: Optional[str] = Field(None, description="Explicit SKU (if omitted, Gemini generates one)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_name": "Timer Faucet BPT-09 Self-Closing Basin Tap",
                "raw_specs": "Material: Solid Brass Construction with Polished Chrome Finish; Mechanism: Hydraulic Auto-Shutoff Cartridge; Timing: 7-12 seconds auto-close delay; Operating Pressure: 0.5 Bar to 6.0 Bar; Flow Rate: 3.0 L/min at 3 Bar; Inlet Connection: G 1/2 inch thread; Dimensions: Overall Height 140 mm, Spout Reach 110 mm, Mounting Hole 32-35 mm",
                "category_id": 121,
                "price": "145.00",
                "focus_keyphrase": "Self-Closing Timer Faucet",
                "image_url": "https://maat.ae/wp-content/uploads/2025/09/BPT-08-1.webp",
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
    seo_title: Optional[str] = None
    meta_description: Optional[str] = None
    slug: Optional[str] = None


class AgentState(TypedDict):
    """State dictionary passed through LangGraph nodes."""
    input_data: Dict[str, Any]
    generated_description: Any
    validation_passed: bool
    validation_error: str
    wordpress_product_id: Optional[int]
    wordpress_product_url: Optional[str]
    internal_link_url: Optional[str]
    writer_attempts: int