// ---------------------------------------------------------------------
// Focus keyphrase suggestion + uniqueness check + slug preview.
//
// Suggestion is a local heuristic (no API call, no extra Gemini cost):
// strips the "MAAT" brand name, model/size codes containing a digit
// (e.g. "BPT-09", "15x15cm"), and filler words from the product name,
// keeping the first 4 remaining words to match the backend's "4 words or
// fewer" keyphrase rule.
//
// Uniqueness is checked against the full history of every focus
// keyphrase ever used on the site (fetched once from
// /api/v1/keyphrase-history), so a duplicate is caught while typing
// instead of after a failed publish.
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

const MAX_KEYPHRASE_WORDS = 4;

const HINT_CLASS =
  "text-[#667085] dark:text-[#9aa4b2] text-[0.78rem] mt-1 empty:hidden";
const WARNING_CLASS =
  "text-red-600 dark:text-red-400 text-[0.78rem] mt-1 font-medium empty:hidden";
const USE_BUTTON_CLASS =
  "bg-transparent border-0 text-blue-600 dark:text-blue-500 font-semibold text-[0.78rem] p-0 cursor-pointer hover:text-blue-700 dark:hover:text-blue-400 hover:underline";
const INPUT_NORMAL_CLASS =
  "w-full px-[0.7rem] py-[0.55rem] border border-[#dde1e6] dark:border-[#2c333b] rounded-md bg-[#f6f7f9] dark:bg-[#14171b] text-[#1c2126] dark:text-[#e6e9ec] text-[0.9rem] font-sans";
const INPUT_ERROR_CLASS =
  "w-full px-[0.7rem] py-[0.55rem] border border-red-500 dark:border-red-500 rounded-md bg-[#f6f7f9] dark:bg-[#14171b] text-[#1c2126] dark:text-[#e6e9ec] text-[0.9rem] font-sans";

function tokenize(productName) {
  return productName.trim().split(/\s+/).filter(Boolean);
}

function isBrandOrStopword(token) {
  const bare = token.toLowerCase().replace(/[^a-z0-9]/g, "");
  return !bare || bare === "maat" || STOPWORDS.has(bare);
}

const isDimensionLike = (token) => /\d+\s*[x×]\s*\d+/i.test(token);

export function suggestKeyphrase(productName) {
  const tokens = tokenize(productName);
  const meaningful = tokens.filter(
    (w) => !isBrandOrStopword(w) && !/\d/.test(w),
  );
  return (meaningful.length ? meaningful : tokens).slice(0, 4).join(" ");
}

// Tries the plain suggestion first, then a handful of alternate word
// combinations (sliding windows over the descriptive words, plus the
// descriptive words paired with a distinguishing model/size code) until
// it finds one `isUsed` rejects, so callers never suggest a keyphrase
// that's already taken. Returns null if every combination is taken.
export function suggestUnusedKeyphrase(productName, isUsed) {
  const tokens = tokenize(productName);
  const meaningful = tokens.filter((w) => !isBrandOrStopword(w));
  const words = meaningful.filter((w) => !/\d/.test(w));
  const modelTokens = meaningful
    .filter((w) => /\d/.test(w))
    .sort((a, b) => Number(isDimensionLike(b)) - Number(isDimensionLike(a)));

  const pool = words.length ? words : tokens;
  const candidates = [];

  for (let start = 0; start < pool.length; start += 1) {
    candidates.push(pool.slice(start, start + 4).join(" "));
    if (start + 4 >= pool.length) break;
  }
  for (const model of modelTokens) {
    candidates.push([...words.slice(0, 3), model].join(" "));
    candidates.push([model, ...words.slice(0, 3)].join(" "));
  }

  const seen = new Set();
  for (const raw of candidates) {
    const candidate = raw.trim().replace(/\s+/g, " ");
    if (!candidate || seen.has(candidate.toLowerCase())) continue;
    seen.add(candidate.toLowerCase());
    if (!isUsed(candidate)) return candidate;
  }
  return null;
}

export function slugify(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export async function loadUsedKeyphrases() {
  try {
    const res = await fetch("/api/v1/keyphrase-history");
    if (!res.ok) throw new Error("failed to load keyphrase history");
    const { keyphrases } = await res.json();
    return new Set((keyphrases || []).map((k) => k.toLowerCase()));
  } catch {
    // Fail open -- the backend still rejects duplicates at publish time,
    // this just loses the live warning while typing.
    return new Set();
  }
}

export function initKeyphraseSuggestion({
  productNameInput,
  focusKeyphraseInput,
  suggestionEl,
  slugPreviewEl,
}) {
  let usedKeyphrases = new Set();
  const isUsed = (kw) => usedKeyphrases.has(kw.trim().toLowerCase());

  function makeUseButton(value) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = USE_BUTTON_CLASS;
    btn.textContent = "Use this";
    btn.addEventListener("click", () => {
      focusKeyphraseInput.value = value;
      renderKeyphraseFeedback();
      renderSlugPreview();
    });
    return btn;
  }

  function clearInputError() {
    focusKeyphraseInput.className = INPUT_NORMAL_CLASS;
    focusKeyphraseInput.removeAttribute("aria-invalid");
  }

  function setInputError() {
    focusKeyphraseInput.className = INPUT_ERROR_CLASS;
    focusKeyphraseInput.setAttribute("aria-invalid", "true");
  }

  // A trimmed-to-4-words version of what the user actually typed, used as
  // the "Try:" alternative for a too-long keyphrase so the fix stays close
  // to their input instead of jumping straight to the product-name-derived
  // suggestion.
  function trimToMaxWords(value) {
    return value.trim().split(/\s+/).filter(Boolean).slice(0, MAX_KEYPHRASE_WORDS).join(" ");
  }

  function renderKeyphraseFeedback() {
    const typed = focusKeyphraseInput.value.trim();

    if (typed) {
      const wordCount = typed.split(/\s+/).filter(Boolean).length;
      const tooLong = wordCount > MAX_KEYPHRASE_WORDS;
      const alreadyUsed = !tooLong && isUsed(typed);

      suggestionEl.replaceChildren();

      if (!tooLong && !alreadyUsed) {
        clearInputError();
        suggestionEl.className = HINT_CLASS;
        return;
      }

      setInputError();
      suggestionEl.className = WARNING_CLASS;
      suggestionEl.append(
        tooLong
          ? `Too long: ${wordCount} words (keep it to ${MAX_KEYPHRASE_WORDS} or fewer).`
          : "Already used on another product.",
      );

      const trimmed = tooLong ? trimToMaxWords(typed) : null;
      const alt =
        trimmed && !isUsed(trimmed)
          ? trimmed
          : suggestUnusedKeyphrase(productNameInput.value, isUsed);
      if (alt && alt.toLowerCase() !== typed.toLowerCase()) {
        suggestionEl.append(" Try: ");
        const em = document.createElement("em");
        em.textContent = alt;
        suggestionEl.append(em, " ", makeUseButton(alt));
      }
      return;
    }

    clearInputError();
    suggestionEl.className = HINT_CLASS;
    suggestionEl.replaceChildren();
    const suggestion = suggestUnusedKeyphrase(productNameInput.value, isUsed);
    if (!suggestion) return;
    suggestionEl.append("Suggested: ");
    const em = document.createElement("em");
    em.textContent = suggestion;
    suggestionEl.append(em, " ", makeUseButton(suggestion));
  }

  function renderSlugPreview() {
    const slug = slugify(focusKeyphraseInput.value);
    slugPreviewEl.textContent = slug
      ? `Likely slug includes: ${slug}-… (final slug is generated at publish time)`
      : "";
  }

  productNameInput.addEventListener("input", renderKeyphraseFeedback);
  focusKeyphraseInput.addEventListener("input", () => {
    renderKeyphraseFeedback();
    renderSlugPreview();
  });

  loadUsedKeyphrases().then((set) => {
    usedKeyphrases = set;
    renderKeyphraseFeedback();
  });
}
