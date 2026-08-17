// ---------------------------------------------------------------------
// Focus keyphrase suggestion + slug preview -- a local heuristic (no API
// call, no extra Gemini cost): strips the "MAAT" brand name, model/part
// codes containing a digit (e.g. "BPT-09"), and filler words from the
// product name, keeping the first 4 remaining words to match the
// backend's "4 words or fewer" keyphrase rule.
// ---------------------------------------------------------------------

const STOPWORDS = new Set([
  "the",
  "a",
  "an",
  "with",
  "for",
  "and",
  "of",
  "in",
  "on",
  "by",
  "to",
]);

export function suggestKeyphrase(productName) {
  const tokens = productName.trim().split(/\s+/).filter(Boolean);
  const meaningful = tokens.filter((w) => {
    const bareWord = w.toLowerCase().replace(/[^a-z0-9]/g, "");
    if (!bareWord || bareWord === "maat" || STOPWORDS.has(bareWord))
      return false;
    return !/\d/.test(w); // drop model/part codes like "BPT-09"
  });
  return (meaningful.length ? meaningful : tokens).slice(0, 4).join(" ");
}

export function slugify(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function initKeyphraseSuggestion({
  productNameInput,
  focusKeyphraseInput,
  suggestionEl,
  slugPreviewEl,
}) {
  function renderKeyphraseSuggestion() {
    const suggestion = suggestKeyphrase(productNameInput.value);
    if (!suggestion || focusKeyphraseInput.value.trim()) {
      suggestionEl.replaceChildren();
      return;
    }
    suggestionEl.replaceChildren();
    suggestionEl.append(`Suggested: `);
    const em = document.createElement("em");
    em.textContent = suggestion;
    suggestionEl.append(em, " ");

    const useBtn = document.createElement("button");
    useBtn.type = "button";
    useBtn.className =
      "bg-transparent border-0 text-blue-600 dark:text-blue-500 font-semibold text-[0.78rem] p-0 cursor-pointer hover:text-blue-700 dark:hover:text-blue-400 hover:underline";
    useBtn.textContent = "Use this";
    useBtn.addEventListener("click", () => {
      focusKeyphraseInput.value = suggestion;
      renderKeyphraseSuggestion();
      renderSlugPreview();
    });
    suggestionEl.append(useBtn);
  }

  function renderSlugPreview() {
    const slug = slugify(focusKeyphraseInput.value);
    slugPreviewEl.textContent = slug
      ? `Likely slug includes: ${slug}-… (final slug is generated at publish time)`
      : "";
  }

  productNameInput.addEventListener("input", renderKeyphraseSuggestion);
  focusKeyphraseInput.addEventListener("input", () => {
    renderKeyphraseSuggestion();
    renderSlugPreview();
  });
}
