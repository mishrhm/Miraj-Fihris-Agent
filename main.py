from fastapi import FastAPI, HTTPException
from app.schemas import ProductRequest, ProductResponse, AgentState
from app.graph import fihris_agent
from app.config import settings
from app.seo_history import was_keyphrase_used
from app.wordpress_media import upload_media

app = FastAPI(
    title="Miraj Fihris Agent",
    description="Autonomous E-Commerce Copywriting & Publishing Agent by MIRAJ Co.",
    version="1.0.0"
)

@app.get("/")
def health_check():
    return {"status": "active", "agent": "Miraj Fihris Agent", "organization": "MIRAJ Co."}

@app.post("/api/v1/publish-product", response_model=ProductResponse)
async def publish_product(req: ProductRequest):
    # Pre-flight checks: these concern the input keyphrase itself, not the
    # generated content, so retrying generation could never fix them.
    keyphrase = req.focus_keyphrase.strip()
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

    input_data = req.model_dump()

    # Upload local images to the WP media library once, up front -- this is
    # a one-shot side effect and shouldn't be repeated on every writer retry.
    if req.image_paths:
        try:
            uploaded = [
                upload_media(path, alt_text=f"{keyphrase} - {req.product_name}")
                for path in req.image_paths
            ]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image upload to WordPress media library failed: {e}")

        input_data["image_url"] = uploaded[0]["url"]
        input_data["gallery_images"] = [{"src": u["url"]} for u in uploaded[1:]]

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)