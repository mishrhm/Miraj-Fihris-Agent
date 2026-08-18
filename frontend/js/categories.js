// ---------------------------------------------------------------------
// Category dropdown / checkbox tree
// ---------------------------------------------------------------------

export function buildCategoryTree(categories) {
  const byId = new Map(categories.map((c) => [c.id, { ...c, children: [] }]));
  const roots = [];
  for (const c of byId.values()) {
    const parent = c.parent && c.parent !== c.id ? byId.get(c.parent) : null;
    if (parent) {
      parent.children.push(c);
    } else {
      roots.push(c);
    }
  }
  const sortSiblings = (nodes) => {
    nodes.sort((a, b) => a.name.localeCompare(b.name));
    for (const n of nodes) sortSiblings(n.children);
  };
  sortSiblings(roots);
  return roots;
}

function flattenTree(nodes, depth = 0, out = []) {
  for (const n of nodes) {
    out.push({ ...n, depth });
    flattenTree(n.children, depth + 1, out);
  }
  return out;
}

export function populateCategorySelect(selectEl, orderedCategories, placeholder) {
  selectEl.innerHTML = placeholder
    ? `<option value="">${placeholder}</option>`
    : "";
  for (const c of orderedCategories) {
    const opt = document.createElement("option");
    opt.value = c.id;
    opt.textContent = "— ".repeat(c.depth) + c.name;
    selectEl.appendChild(opt);
  }
}

function renderCategoryCheckboxes(containerEl, nodes, depth = 0) {
  for (const node of nodes) {
    const row = document.createElement("label");
    row.className =
      "flex items-center gap-2 py-[0.2rem] text-[0.85rem] cursor-pointer" +
      (depth === 0
        ? " font-semibold"
        : " font-normal text-[#42505f] dark:text-[#c2c9d1]");
    row.style.paddingLeft = `${depth * 1.1}rem`;

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.name = "additional_category_ids";
    checkbox.value = node.id;
    checkbox.className = "shrink-0";

    const span = document.createElement("span");
    span.textContent = node.name;

    row.appendChild(checkbox);
    row.appendChild(span);
    containerEl.appendChild(row);

    if (node.children.length) {
      renderCategoryCheckboxes(containerEl, node.children, depth + 1);
    }
  }
}

export function populateCategoryCheckboxTree(containerEl, tree) {
  containerEl.innerHTML = "";
  if (!tree.length) {
    containerEl.innerHTML =
      '<p class="text-[0.85rem] text-[#667085] dark:text-[#9aa4b2] m-0">No categories available.</p>';
    return;
  }
  renderCategoryCheckboxes(containerEl, tree);
}

export async function loadCategories(categoryId, additionalCategoriesContainer) {
  try {
    const res = await fetch("/api/v1/categories");
    if (!res.ok) throw new Error("failed to load categories");
    const { categories } = await res.json();
    const tree = buildCategoryTree(categories);
    populateCategorySelect(categoryId, flattenTree(tree), "Select a category…");
    populateCategoryCheckboxTree(additionalCategoriesContainer, tree);
  } catch {
    populateCategorySelect(
      categoryId,
      [],
      "Could not load categories — try reloading the page",
    );
    additionalCategoriesContainer.innerHTML =
      '<p class="text-[0.85rem] text-red-600 dark:text-red-400 m-0">Could not load categories — try reloading the page.</p>';
  }
}

export function initCategoryFields({ categoryId, additionalCategoryIds, clearButton }) {
  clearButton.addEventListener("click", () => {
    for (const checkbox of additionalCategoryIds.querySelectorAll(
      'input[type="checkbox"]',
    )) {
      checkbox.checked = false;
    }
  });

  loadCategories(categoryId, additionalCategoryIds);
}
