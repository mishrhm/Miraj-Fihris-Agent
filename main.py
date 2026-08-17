from fastapi import FastAPI, HTTPException
from app.schemas import ProductRequest, AgentState
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

@app.post("/api/v1/publish-product")
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
        return {
            "status": "success",
            "wordpress_product_id": final_state["wordpress_product_id"],
            "wordpress_product_url": final_state["wordpress_product_url"],
            "generated_description": final_state["generated_description"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)