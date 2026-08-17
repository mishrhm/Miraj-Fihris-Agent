import re
from typing import Dict, Any
from langgraph.graph import StateGraph, END

from app.schemas import AgentState
from app.gemini import generate_product_copy
from app.woocommerce import publish_to_woocommerce

def writer_node(state: AgentState) -> Dict[str, Any]:
    data = state["input_data"]
    
    copy = generate_product_copy(
        name=data["product_name"],
        specs=data["raw_specs"],
        focus_keyphrase=data.get("focus_keyphrase", "Auto-Derived Keyphrase"),
        sku=data.get("sku", ""),
        feedback_error=state.get("validation_error", "")
    )

    return {
        "generated_description": copy,
        "validation_passed": False,
        "validation_error": ""
    }
    
def validator_node(state: AgentState) -> Dict[str, Any]:
    content = state["generated_description"]

    # Defensive check: ensure content is a string
    if isinstance(content, dict):
        content = content.get("description", str(content))

    errors = []

    # Rule 1: No LaTeX allowed
    if "$" in content or "\\text" in content:
        errors.append("LaTeX formatting detected. All dimensions must be plain text (e.g., 10 cm x 10 cm).")

    # Rule 2: Forbidden Phrases
    if re.search(r"new arrival", content, re.IGNORECASE):
        errors.append("Forbidden phrase detected.")

    # Rule 3: Word Count Threshold
    word_count = len(content.split())
    if word_count < 280:
        errors.append(f"Description too short ({word_count} words). Target is ~350 words.")

    if errors:
        return {"validation_passed": False, "validation_error": " | ".join(errors)}

    return {"validation_passed": True, "validation_error": ""}

def publisher_node(state: AgentState) -> Dict[str, Any]:
    data = state["input_data"]
    res = publish_to_woocommerce(
        product_name=data["product_name"],
        description=state["generated_description"],
        price=data["price"],
        category_id=data["category_id"],
        image_url=data.get("image_url"),
        sku=data.get("sku", ""),
    )
    return {
        "wordpress_product_id": res["id"],
        "wordpress_product_url": res["url"]
    }

def routing_logic(state: AgentState) -> str:
    if state["validation_passed"]:
        return "publisher"
    return "writer"

workflow = StateGraph(AgentState)
workflow.add_node("writer", writer_node)
workflow.add_node("validator", validator_node)
workflow.add_node("publisher", publisher_node)

workflow.set_entry_point("writer")
workflow.add_edge("writer", "validator")

workflow.add_conditional_edges(
    "validator",
    routing_logic,
    {
        "publisher": "publisher",
        "writer": "writer"
    }
)

workflow.add_edge("publisher", END)
fihris_agent = workflow.compile()