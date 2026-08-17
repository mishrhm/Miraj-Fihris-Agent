import os
from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException, Form, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.schemas import ProductRequest, ProductResponse, AgentState
from app.graph import fihris_agent
from app.config import settings
from app.seo_history import was_keyphrase_used
from app.wordpress_media import upload_media, upload_media_bytes
from app.woocommerce import list_categories

app = FastAPI(
    title="Miraj Fihris Agent",
    description="Autonomous E-Commerce Copywriting & Publishing Agent by MIRAJ Co.",
    version="1.0.0"
)

@app.get("/")
def health_check():
    return {"status": "active", "agent": "Miraj Fihris Agent", "organization": "MIRAJ Co."}

_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
_FRONTEND_INDEX = os.path.join(_FRONTEND_DIR, "index.html")
app.mount("/upload-assets", StaticFiles(directory=_FRONTEND_DIR), name="upload-assets")

@app.get("/upload")
def upload_page():
    return FileResponse(_FRONTEND_INDEX)

@app.get("/api/v1/categories")
def get_categories():
    try:
        categories = list_categories()
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch WooCommerce categories: {e}")
    return {"categories": categories}


async def _run_publish_pipeline(
    input_data: dict[str, Any],
    focus_keyphrase: str,
    uploaded_images: Optional[list[dict[str, Any]]] = None,
) -> ProductResponse:
    # Pre-flight checks: these concern the input keyphrase itself, not the
    # generated content, so retrying generation could never fix them.
    keyphrase = focus_keyphrase.strip()
    if len(keyphrase.split()) > 4:
        raise HTTPException(
            status_code=400,
            detail=f"Keyphrase length: focus_keyphrase '{keyphrase}' is too long ({len(keyphrase.split())} words). Keep it to 4 words or fewer."
        )
    if was_keyphrase_used(keyphrase):
        raise HTTPException(
            status_code=400,
            detail=f"Previously used keyphrase: '{keyphrase}' has already been used on another product. Choose a keyphrase you haven't used before."
        )

    if uploaded_images:
        input_data["image_url"] = uploaded_images[0]["url"]
        input_data["gallery_images"] = [{"src": u["url"]} for u in uploaded_images[1:]]

    initial_state: AgentState = {
        "input_data": input_data,
        "generated_description": "",
        "validation_passed": False,
        "validation_error": "",
        "wordpress_product_id": None,
        "wordpress_product_url": None,
        "internal_link_url": None,
        "writer_attempts": 0
    }

    try:
        final_state = fihris_agent.invoke(initial_state)

        if not final_state.get("wordpress_product_id"):
            raise HTTPException(
                status_code=422,
                detail=f"Could not produce a listing that passes SEO validation: {final_state.get('validation_error', 'unknown error')}"
            )

        # Safely extract plain text description if returned as a dict from state
        raw_desc = final_state.get("generated_description", "")
        if isinstance(raw_desc, dict):
            desc_text = raw_desc.get("description", "")
            seo_title = raw_desc.get("seo_title")
            meta_description = raw_desc.get("meta_description")
            slug = raw_desc.get("slug")
        else:
            desc_text = str(raw_desc)
            seo_title = meta_description = slug = None

        # Retrieve final SKU from the graph execution state
        sku_val = final_state.get("input_data", {}).get("sku")

        return ProductResponse(
            status="success",
            wordpress_product_id=final_state["wordpress_product_id"],
            wordpress_product_url=final_state["wordpress_product_url"],
            generated_description=desc_text,
            sku=sku_val,
            seo_title=seo_title,
            meta_description=meta_description,
            slug=slug
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/publish-product", response_model=ProductResponse)
async def publish_product(req: ProductRequest):
    input_data = req.model_dump()

    # Upload local images to the WP media library once, up front -- this is
    # a one-shot side effect and shouldn't be repeated on every writer retry.
    uploaded = None
    if req.image_paths:
        try:
            uploaded = [
                upload_media(path, alt_text=f"{req.focus_keyphrase.strip()} - {req.product_name}")
                for path in req.image_paths
            ]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image upload to WordPress media library failed: {e}")

    return await _run_publish_pipeline(input_data, req.focus_keyphrase, uploaded)


@app.post("/api/v1/publish-product-form", response_model=ProductResponse)
async def publish_product_form(
    product_name: str = Form(...),
    raw_specs: str = Form(...),
    category_id: int = Form(...),
    additional_category_ids: Optional[List[int]] = Form(None),
    price: Optional[str] = Form(None),
    focus_keyphrase: str = Form(...),
    brand: Optional[str] = Form(None),
    sku: Optional[str] = Form(None),
    product_photos: List[UploadFile] = File(default_factory=list),
):
    """Browser-facing counterpart to /api/v1/publish-product: accepts real
    uploaded photo bytes (a browser can't hand the server a local file
    path) instead of image_paths, then runs the same publish pipeline."""
    photos = [p for p in product_photos if p.filename]
    try:
        uploaded = [
            upload_media_bytes(
                await photo.read(),
                photo.filename or "product-photo.webp",
                alt_text=f"{focus_keyphrase.strip()} - {product_name}",
            )
            for photo in photos
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image upload to WordPress media library failed: {e}")

    input_data = {
        "product_name": product_name,
        "raw_specs": raw_specs,
        "category_id": category_id,
        "additional_category_ids": additional_category_ids,
        "price": price,
        "focus_keyphrase": focus_keyphrase,
        "brand": brand,
        "sku": sku,
    }

    return await _run_publish_pipeline(input_data, focus_keyphrase, uploaded)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)
