import { initCategoryFields } from "./categories.js";
import { initPhotoValidation } from "./photo-validation.js";
import { initKeyphraseSuggestion } from "./keyphrase.js";

const RESULT_BASE = "mt-4 rounded-lg px-5 py-4 text-[0.88rem] whitespace-pre-wrap";
const RESULT_OK = "block bg-[#ecfdf3] dark:bg-[#0f2a1a] text-green-700 dark:text-green-400";
const RESULT_BAD = "block bg-red-50 dark:bg-[#2a1414] text-red-700 dark:text-red-400";
const RESULT_HIDDEN = "hidden";

const form = document.getElementById("product-form");
const el = {
  productName: document.getElementById("product_name"),
  categoryId: document.getElementById("category_id"),
  additionalCategoryIds: document.getElementById("additional_category_ids"),
  clearAdditionalCategories: document.getElementById(
    "clear-additional-categories",
  ),
  focusKeyphrase: document.getElementById("focus_keyphrase"),
  keyphraseSuggestion: document.getElementById("keyphrase-suggestion"),
  slugPreview: document.getElementById("slug-preview"),
  productPhotos: document.getElementById("product_photos"),
  photoStatus: document.getElementById("photo-status"),
  submitBtn: document.getElementById("submit-btn"),
  result: document.getElementById("result"),
};

initCategoryFields({
  categoryId: el.categoryId,
  additionalCategoryIds: el.additionalCategoryIds,
  clearButton: el.clearAdditionalCategories,
});

initPhotoValidation({
  input: el.productPhotos,
  statusContainer: el.photoStatus,
});

initKeyphraseSuggestion({
  productNameInput: el.productName,
  focusKeyphraseInput: el.focusKeyphrase,
  suggestionEl: el.keyphraseSuggestion,
  slugPreviewEl: el.slugPreview,
});

// ---------------------------------------------------------------------
// Submit
// ---------------------------------------------------------------------

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  el.result.className = RESULT_HIDDEN;
  el.result.textContent = "";
  el.submitBtn.disabled = true;
  el.submitBtn.textContent = "Publishing…";

  // Form fields' `name` attributes already match the backend's expected
  // field names, including repeated entries for the multi-select and
  // multi-file inputs, so the native FormData(form) needs no manual
  // per-field assembly.
  const formData = new FormData(form);

  try {
    const res = await fetch("/api/v1/publish-product-form", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Publish failed.");

    el.result.className = `${RESULT_BASE} ${RESULT_OK}`;
    el.result.innerHTML =
      `Published: <a class="text-inherit font-bold" href="${data.wordpress_product_url}" target="_blank">${data.wordpress_product_url}</a>\n` +
      `SKU: ${data.sku || "—"}\nSEO title: ${data.seo_title || "—"}\nMeta description: ${data.meta_description || "—"}`;
  } catch (err) {
    el.result.className = `${RESULT_BASE} ${RESULT_BAD}`;
    el.result.textContent = err.message;
  } finally {
    el.submitBtn.disabled = false;
    el.submitBtn.textContent = "Publish Product";
  }
});
