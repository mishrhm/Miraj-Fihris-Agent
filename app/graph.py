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

def publisher_node(state: AgentState) -> dict[str, Any]:
    raw_desc = state.get("generated_description", "")
    input_data = state.get("input_data", {})

    desc_text = ""
    # Check if raw_desc is a dictionary before accessing dictionary keys
    if isinstance(raw_desc, dict):
        desc_text = str(raw_desc.get("description", ""))
        gen_sku = raw_desc.get("sku")
        if gen_sku and isinstance(input_data, dict) and not input_data.get("sku"):
            input_data["sku"] = gen_sku
    else:
        desc_text = str(raw_desc)

    product_name = input_data.get("product_name", "") if isinstance(input_data, dict) else ""
    price = input_data.get("price", "0") if isinstance(input_data, dict) else "0"
    category_id = input_data.get("category_id", 0) if isinstance(input_data, dict) else 0
    sku = input_data.get("sku", "") if isinstance(input_data, dict) else ""
    image_url = input_data.get("image_url") if isinstance(input_data, dict) else None

    result = publish_to_woocommerce(
        product_name=product_name,
        description=desc_text,
        price=price,
        category_id=category_id,
        sku=sku,
        image_url=image_url
    )

    return {
        "wordpress_product_id": result["id"],
        "wordpress_product_url": result["url"],
        "generated_description": desc_text
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