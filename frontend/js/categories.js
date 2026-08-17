// ---------------------------------------------------------------------
// Category dropdowns
// ---------------------------------------------------------------------

export function withDepth(categories) {
  const byId = new Map(categories.map((c) => [c.id, c]));
  const depthOf = (cat) => {
    const seen = new Set();
    let depth = 0,
      cur = cat;
    while (
      cur &&
      cur.parent &&
      byId.has(cur.parent) &&
      !seen.has(cur.parent)
    ) {
      seen.add(cur.parent);
      cur = byId.get(cur.parent);
      depth++;
    }
    return depth;
  };
  return categories.map((c) => ({ ...c, depth: depthOf(c) }));
}

export function populateCategorySelect(selectEl, categories, placeholder) {
  selectEl.innerHTML = placeholder
    ? `<option value="">${placeholder}</option>`
    : "";
  for (const c of categories) {
    const opt = document.createElement("option");
    opt.value = c.id;
    opt.textContent = "— ".repeat(c.depth) + c.name;
    selectEl.appendChild(opt);
  }
}

export async function loadCategories(categoryId, additionalCategoryIds) {
  try {
    const res = await fetch("/api/v1/categories");
    if (!res.ok) throw new Error("failed to load categories");
    const { categories } = await res.json();
    const withDepthCategories = withDepth(categories);
    populateCategorySelect(categoryId, withDepthCategories, "Select a category…");
    populateCategorySelect(additionalCategoryIds, withDepthCategories, null);
  } catch {
    populateCategorySelect(
      categoryId,
      [],
      "Could not load categories — try reloading the page",
    );
  }
}

export function initCategoryFields({ categoryId, additionalCategoryIds, clearButton }) {
  clearButton.addEventListener("click", () => {
    for (const opt of additionalCategoryIds.options) opt.selected = false;
  });

  loadCategories(categoryId, additionalCategoryIds);
}
