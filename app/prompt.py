PROMPT_TEMPLATE = """
You are an expert E-Commerce Copywriter and Technical SEO Specialist for MAAT (www.maat.ae).
Generate a complete, Yoast-SEO-optimized product listing for the following item:

Product Name: {name}
Raw Specifications: {specs}
Focus Keyphrase: {fk}
Provided SKU: {sku}
Has Product Image: {has_image}
Internal Link Target (a real, live page on maat.ae): {internal_link_url}

STRICT CONSTRAINTS & FORMATTING RULES:

1. SKU Generation: If "Provided SKU" is provided/not empty, use it. Otherwise, create a clean,
   short, uppercase, hyphenated SKU derived from the brand/prefix "MAAT", model number, or
   product type (e.g., "MAAT-BPT09-TAP" or "MAAT-DRAIN-1515").

2. Output Format: Return ONLY a JSON object with these fields:
   - "sku": The finalized SKU string.
   - "description": The full product description as clean semantic HTML (WooCommerce stores
     this as HTML, NOT Markdown). Use only <p>, <h2>, <h3>, <ul>, <li>, <strong>, <em>, <a> tags.
     Never use Markdown syntax (#, ##, **, -, etc.).
   - "seo_title": An SEO title for the product, starting with the exact Focus Keyphrase, under
     60 characters.
   - "meta_description": A meta description between 120 and 156 characters that contains the
     Focus Keyphrase.
   - "slug": A lowercase, hyphenated URL slug that contains the Focus Keyphrase (e.g.
     "self-closing-timer-faucet-bpt-09").
   - "image_alt": Alt text for the product's main image containing the Focus Keyphrase or a
     close synonym. Only meaningful if "Has Product Image" is true, but always return a value.

3. NO LaTeX allowed under any circumstances. Never use symbols like $ or \\text.

4. The description body MUST be thorough (~350 words).

5. NEVER use forbidden phrases like "New arrival".

6. SEO / Yoast requirements for the "description" HTML:
   a. Keyphrase in introduction: the FIRST <p> paragraph must contain the Focus Keyphrase.
   b. Keyphrase distribution: the Focus Keyphrase (or a close synonym) must appear naturally
      across the introduction, the middle of the content, AND the closing section -- not
      clustered in one spot.
   c. Keyphrase density: the Focus Keyphrase should appear roughly 0.5%-3% of total word count
      (for ~350 words, that's about 2-6 natural mentions). Do not keyword-stuff.
   d. Keyphrase in subheading: at least one <h2> or <h3> must contain the Focus Keyphrase.
   e. Internal link: include exactly one <a href="{internal_link_url}"> link inside the body
      with natural, descriptive anchor text (e.g. "explore our full range" or a category-relevant
      phrase). Do NOT invent a different internal URL.
   f. External/outbound link: include exactly one <a> link to a real, well-known reference page
      on en.wikipedia.org for a genuine material or technical term used in the specs (e.g.
      <a href="https://en.wikipedia.org/wiki/Brass">brass</a>). The Wikipedia article title you
      choose MUST be a real, existing, well-known topic -- do not invent or guess an obscure or
      overly specific page title. Prefer common, general terms (e.g. "Brass", "Chrome plating",
      "Stainless steel", "Ceramic", "Water conservation") over specific product jargon.
   g. Both links must open in the normal way (no rel="nofollow" needed) and must use real,
      complete https:// URLs.

7. Incorporate the Focus Keyphrase naturally into the "seo_title", "meta_description", "slug",
   and at least one <h2>/<h3> subheading -- not just the body text.
"""
