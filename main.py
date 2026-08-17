from fastapi import FastAPI, HTTPException
from app.schemas import ProductRequest, ProductResponse, AgentState
from app.graph import fihris_agent
from app.config import settings

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
    initial_state: AgentState = {
        "input_data": req.model_dump(),
        "generated_description": "",
        "validation_passed": False,
        "validation_error": "",
        "wordpress_product_id": None,
        "wordpress_product_url": None
    }

    try:
        final_state = fihris_agent.invoke(initial_state)

        # Safely extract plain text description if returned as a dict from state
        raw_desc = final_state.get("generated_description", "")
        if isinstance(raw_desc, dict):
            desc_text = raw_desc.get("description", "")
        else:
            desc_text = str(raw_desc)

        # Retrieve final SKU from the graph execution state
        sku_val = final_state.get("input_data", {}).get("sku")

        return ProductResponse(
            status="success",
            wordpress_product_id=final_state["wordpress_product_id"],
            wordpress_product_url=final_state["wordpress_product_url"],
            generated_description=desc_text,
            sku=sku_val
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)