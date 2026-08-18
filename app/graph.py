import re
from typing import Dict, Any
from bs4 import BeautifulSoup
from langgraph.graph import StateGraph, END

from app.config import settings
from app.schemas import AgentState
from app.gemini import generate_product_copy
from app.woocommerce import publish_to_woocommerce, get_category_permalink, url_is_reachable
from app.seo_history import record_keyphrase

MAX_WRITER_ATTEMPTS = 5
MIN_KEYPHRASE_DENSITY = 0.5
MAX_KEYPHRASE_DENSITY = 3.0
MIN_META_DESC_LEN = 120
MAX_META_DESC_LEN = 156


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def writer_node(state: AgentState) -> Dict[str, Any]:
    data = state["input_data"]

    internal_link_url = state.get("internal_link_url")
    if not internal_link_url:
        internal_link_url = get_category_permalink(data.get("category_id", 0)) or f"{settings.WC_URL}/"

    copy = generate_product_copy(
        name=data["product_name"],
        specs=data["raw_specs"],
        focus_keyphrase=data.get("focus_keyphrase", "Auto-Derived Keyphrase"),
        sku=data.get("sku", ""),
        brand=data.get("brand", "") or "",
        feedback_error=state.get("validation_error", ""),
        has_image=bool(data.get("image_url")),
        internal_link_url=internal_link_url
    )

    return {
        "generated_description": copy,
        "validation_passed": False,
        "validation_error": "",
        "internal_link_url": internal_link_url,
        "writer_attempts": state.get("writer_attempts", 0) + 1
    }


def validator_node(state: AgentState) -> Dict[str, Any]:
    generated = state["generated_description"]
    input_data = state.get("input_data", {})
    internal_link_url = state.get("internal_link_url", "")

    if not isinstance(generated, dict):
        return {"validation_passed": False, "validation_error": "Generator did not return structured JSON output."}

    content_html = str(generated.get("description", ""))
    seo_title = str(generated.get("seo_title", ""))
    meta_description = str(generated.get("meta_description", ""))
    slug = str(generated.get("slug", ""))
    image_alt = str(generated.get("image_alt", ""))
    synonyms = [str(s).strip() for s in (generated.get("keyphrase_synonyms") or []) if str(s).strip()]
    attributes = generated.get("attributes") or []
    keyphrase = str(input_data.get("focus_keyphrase", "")).strip()
    kp_lower = keyphrase.lower()
    has_image = bool(input_data.get("image_url"))

    errors = []

    # --- Structural / formatting rules ---
    if "$" in content_html or "\\text" in content_html:
        errors.append("LaTeX formatting detected. All dimensions must be plain text (e.g., 10 cm x 10 cm).")

    if re.search(r"new arrival", content_html, re.IGNORECASE):
        errors.append("Forbidden phrase detected.")

    if re.search(r"^\s{0,3}#{1,6}\s|\*\*", content_html, re.MULTILINE):
        errors.append("Markdown syntax detected in description. Output must be clean HTML (<p>, <h2>, <h3>, <ul>, <strong>), not Markdown.")

    soup = BeautifulSoup(content_html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    words = text.split()
    word_count = len(words)

    if word_count < 280:
        errors.append(f"Description too short ({word_count} words). Target is ~350 words.")

    if not keyphrase:
        errors.append("No focus keyphrase available to validate against.")
        return {"validation_passed": False, "validation_error": " | ".join(errors)}

    kp_pattern = re.compile(re.escape(keyphrase), re.IGNORECASE)
    kp_or_synonym_pattern = re.compile(
        "|".join(re.escape(t) for t in [keyphrase, *synonyms] if t), re.IGNORECASE
    ) if keyphrase else None

    # --- Keyphrase in introduction ---
    paragraphs = [p.get_text(separator=" ", strip=True) for p in soup.find_all("p")]
    if not paragraphs or not kp_pattern.search(paragraphs[0]):
        errors.append(f"Keyphrase in introduction: the opening paragraph must contain the focus keyphrase '{keyphrase}'.")

    # --- Keyphrase distribution: no oversized gap between mentions ---
    # Mirrors Yoast's real distribution check (which credits the keyphrase and
    # its synonyms) by looking at gaps between sentence-level hits, rather than
    # just requiring presence in 2 of 3 coarse thirds -- a check that could
    # still pass while leaving an entire half of the text without a mention.
    if kp_or_synonym_pattern and text:
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        n_sentences = len(sentences)
        if n_sentences > 0:
            hit_indices = [i for i, s in enumerate(sentences) if kp_or_synonym_pattern.search(s)]
            if not hit_indices:
                errors.append(
                    f"Keyphrase distribution: the focus keyphrase '{keyphrase}' (or a synonym) does not appear in the body text at all."
                )
            else:
                gaps = (
                    [hit_indices[0]]
                    + [b - a for a, b in zip(hit_indices, hit_indices[1:])]
                    + [(n_sentences - 1) - hit_indices[-1]]
                )
                max_allowed_gap = max(round(n_sentences * 0.35), 3)
                largest_gap = max(gaps)
                if largest_gap > max_allowed_gap:
                    errors.append(
                        f"Keyphrase distribution: uneven. There is a stretch of {largest_gap} sentences in a row "
                        f"without the focus keyphrase or a synonym. Distribute mentions of the keyphrase or its "
                        f"synonyms more evenly across the whole text (no gap larger than ~{max_allowed_gap} sentences)."
                    )

    # --- Keyphrase density ---
    occurrences = len(kp_pattern.findall(text))
    density = (occurrences / word_count * 100) if word_count else 0
    if occurrences == 0:
        errors.append(f"Keyphrase density: the focus keyphrase '{keyphrase}' does not appear in the body text at all.")
    elif density < MIN_KEYPHRASE_DENSITY:
        errors.append(f"Keyphrase density too low ({density:.2f}%). Use the focus keyphrase a few more times naturally (target 0.5%-3%).")
    elif density > MAX_KEYPHRASE_DENSITY:
        errors.append(f"Keyphrase density too high ({density:.2f}%), reads as keyword stuffing. Reduce repetitions (target 0.5%-3%).")

    # --- Keyphrase in subheading ---
    subheadings = [h.get_text(separator=" ", strip=True) for h in soup.find_all(["h2", "h3"])]
    if not any(kp_pattern.search(h) for h in subheadings):
        errors.append(f"Keyphrase in subheading: at least one <h2>/<h3> must contain the focus keyphrase '{keyphrase}'.")

    # --- Keyphrase in SEO title ---
    if not seo_title:
        errors.append("Keyphrase in SEO title: no seo_title was generated.")
    elif not seo_title.strip().lower().startswith(kp_lower):
        errors.append(f"Keyphrase in SEO title: seo_title must begin with the focus keyphrase '{keyphrase}'.")
    elif len(seo_title) > 60:
        errors.append(f"SEO title too long ({len(seo_title)} chars). Keep it under 60 characters.")

    # --- Meta description ---
    if not meta_description:
        errors.append("Keyphrase in meta description: no meta_description was generated.")
    else:
        if kp_lower not in meta_description.lower():
            errors.append(f"Keyphrase in meta description: meta_description must contain the focus keyphrase '{keyphrase}'.")
        if len(meta_description) < MIN_META_DESC_LEN or len(meta_description) > MAX_META_DESC_LEN:
            errors.append(f"Meta description length is {len(meta_description)} chars; must be between {MIN_META_DESC_LEN} and {MAX_META_DESC_LEN} characters.")

    # --- Keyphrase in slug ---
    kp_slug = _slugify(keyphrase)
    if not slug:
        errors.append("Keyphrase in slug: no slug was generated.")
    elif kp_slug not in _slugify(slug):
        errors.append(f"Keyphrase in slug: slug must contain the focus keyphrase (expected something containing '{kp_slug}').")

    # --- Keyphrase in image alt attributes ---
    if has_image:
        if not image_alt or kp_lower not in image_alt.lower():
            errors.append(f"Keyphrase in image alt attributes: image_alt must contain the focus keyphrase '{keyphrase}'.")

    # --- Product attributes: structured specs must be parsed out of raw_specs ---
    raw_specs = str(input_data.get("raw_specs", ""))
    if len(raw_specs.strip()) > 40 and len(attributes) < 2:
        errors.append(
            "Product attributes: extract at least 2 structured attributes (e.g. Material, "
            "Dimensions, Finish) from the raw specifications into the 'attributes' field."
        )

    # --- Internal links ---
    links = soup.find_all("a")
    site_host = settings.WC_URL.split("//")[-1].replace("www.", "")

    internal_links = [a for a in links if a.get("href") and (site_host in a.get("href") or a.get("href", "").startswith("/"))]
    if not internal_links:
        errors.append(f"Internal links: add one <a> link inside the description pointing to {internal_link_url}.")

    # --- Outbound (external) links ---
    external_links = [a for a in links if a.get("href", "").startswith("http") and site_host not in a.get("href", "")]
    if not external_links:
        errors.append("Outbound links: add one <a> link to a real, well-known external reference (e.g. a Wikipedia article on a material/spec term used in this product).")
    else:
        href = external_links[0].get("href")
        if not url_is_reachable(href):
            errors.append(f"Outbound link '{href}' does not resolve. Use a real, well-known Wikipedia article title instead of an invented/obscure one.")

    if errors:
        return {"validation_passed": False, "validation_error": " | ".join(errors)}

    return {"validation_passed": True, "validation_error": ""}


def publisher_node(state: AgentState) -> Dict[str, Any]:
    raw_desc = state.get("generated_description", "")
    input_data = state.get("input_data", {})

    if isinstance(raw_desc, dict):
        desc_text = str(raw_desc.get("description", ""))
        seo_title = str(raw_desc.get("seo_title", ""))
        meta_description = str(raw_desc.get("meta_description", ""))
        slug = str(raw_desc.get("slug", ""))
        image_alt = str(raw_desc.get("image_alt", ""))
        attributes = raw_desc.get("attributes") or []
        gen_sku = raw_desc.get("sku")
        if gen_sku and isinstance(input_data, dict) and not input_data.get("sku"):
            input_data["sku"] = gen_sku
    else:
        desc_text = str(raw_desc)
        seo_title = meta_description = slug = image_alt = ""
        attributes = []

    product_name = input_data.get("product_name", "") if isinstance(input_data, dict) else ""
    price = input_data.get("price") if isinstance(input_data, dict) else None
    category_id = input_data.get("category_id", 0) if isinstance(input_data, dict) else 0
    additional_category_ids = input_data.get("additional_category_ids") if isinstance(input_data, dict) else None
    sku = input_data.get("sku", "") if isinstance(input_data, dict) else ""
    image_url = input_data.get("image_url") if isinstance(input_data, dict) else None
    gallery_images = input_data.get("gallery_images") if isinstance(input_data, dict) else None
    focus_keyphrase = input_data.get("focus_keyphrase", "") if isinstance(input_data, dict) else ""
    brand = input_data.get("brand", "") if isinstance(input_data, dict) else ""

    images = []
    if image_url:
        images.append({"src": image_url, "alt": image_alt} if image_alt else {"src": image_url})
    images.extend(gallery_images or [])

    result = publish_to_woocommerce(
        product_name=product_name,
        description=desc_text,
        price=price,
        category_id=category_id,
        additional_category_ids=additional_category_ids,
        sku=sku,
        images=images,
        slug=slug,
        seo_title=seo_title,
        meta_description=meta_description,
        focus_keyphrase=focus_keyphrase,
        brand=brand or "",
        attributes=attributes
    )

    if focus_keyphrase:
        record_keyphrase(focus_keyphrase)

    return {
        "wordpress_product_id": result["id"],
        "wordpress_product_url": result["url"],
        "generated_description": {
            "description": desc_text,
            "sku": sku,
            "seo_title": seo_title,
            "meta_description": meta_description,
            "slug": slug,
            "image_alt": image_alt
        }
    }


def give_up_node(state: AgentState) -> Dict[str, Any]:
    return {
        "validation_error": f"Exceeded {MAX_WRITER_ATTEMPTS} generation attempts. Last validation error: {state.get('validation_error', '')}"
    }


def routing_logic(state: AgentState) -> str:
    if state["validation_passed"]:
        return "publisher"
    if state.get("writer_attempts", 0) >= MAX_WRITER_ATTEMPTS:
        return "give_up"
    return "writer"


workflow = StateGraph(AgentState)
workflow.add_node("writer", writer_node)
workflow.add_node("validator", validator_node)
workflow.add_node("publisher", publisher_node)
workflow.add_node("give_up", give_up_node)

workflow.set_entry_point("writer")
workflow.add_edge("writer", "validator")

workflow.add_conditional_edges(
    "validator",
    routing_logic,
    {
        "publisher": "publisher",
        "writer": "writer",
        "give_up": "give_up"
    }
)

workflow.add_edge("publisher", END)
workflow.add_edge("give_up", END)
fihris_agent = workflow.compile()
