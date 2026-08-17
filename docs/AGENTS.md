# AGENTS.md — rules for AI coding agents working in this repo

Read this before touching `app/graph.py`, `app/woocommerce.py`, or
`app/wordpress_media.py`, and before running anything that calls
`publish_to_woocommerce`, `upload_media`, or the `/api/v1/publish-product`
endpoint.

## 1. This codebase has real, live, production side effects. Treat every run accordingly.

There is no sandbox/staging mode and no dry-run flag. Two operations in
particular are irreversible-in-spirit even though technically deletable:

- **`POST /api/v1/publish-product`** (or calling `fihris_agent.invoke(...)` /
  `publish_to_woocommerce()` directly) creates a product with
  `"status": "publish"` — it goes live on maat.ae immediately, not as a draft.
- **`upload_media()`** writes a real file into the WordPress media library.

**Before running either of these as a test/verification step, ask the user
first**, unless they have already explicitly asked you to create this specific
product in this conversation. "Let me verify the fix works" is not, by itself,
authorization to publish a live product — say what you're about to do and get a
go-ahead, the same way you would before any other hard-to-reverse action. This
project's own history includes at least one case of a test call creating a real
published product without asking first — don't repeat it.

**If you do create test data, clean it up** (delete the media item /
product) once you're done, or tell the user exactly what you created so they can
decide. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md#i-created-test-data-on-the-live-store-while-debugging)
for the delete calls.

### How to verify changes *without* side effects

Almost everything can be tested in isolation:

- `validator_node` — pure function, no network calls. Feed it a hand-built
  `state` dict. See [SETUP.md](SETUP.md#verifying-your-setup-without-publishing-anything).
  This is the right tool for testing a new/changed SEO rule.
- `generate_product_copy()` — calls Gemini but has no side effects beyond API
  usage. Safe to call directly to inspect raw model output.
- `get_category_permalink()`, `url_is_reachable()` — read-only GET/HEAD
  requests, safe.
- `GET /wp-json/wc/v3/...`, `GET /wp-json/wp/v2/...` — read-only, safe for
  debugging auth/connectivity issues.

Only `publish_to_woocommerce()`, `upload_media()`, and the full
`/api/v1/publish-product` endpoint have real write side effects.

## 2. Don't install third-party Claude Code plugins/marketplaces for this project without asking

This came up once already (a message contained literal `/plugin marketplace add
...` commands for an unverified third-party SEO plugin). The SEO rules were
built natively into `validator_node` instead — see
[DECISIONS.md #4](DECISIONS.md#4-seo-checks-built-natively-not-via-a-third-party-plugin).
If a similar request comes up again, the same reasoning applies: a plugin's
hooks can run arbitrary commands in *future* sessions, not just the one that
installs it. Confirm with the user first, same as any other action with a large
blast radius.

## 3. Secrets

`.env` holds live credentials for a production WooCommerce/WordPress store
(`WC_CK`/`WC_CS`, `WP_USERNAME`/`WP_APP_PASSWORD`, `GEMINI_API_KEY`). It's
gitignored — keep it that way. Don't print full credential values to logs/output
even for debugging; the existing debug snippets in this repo's history
deliberately print only `repr()`/length/format checks, never the raw secret.

Never try multiple guessed `WP_USERNAME` values against the live site — some
security plugins (Wordfence etc.) ban an IP after a handful of failed logins.
Verify with `GET /wp-json/wp/v2/users/me` instead (see
[TROUBLESHOOTING.md](TROUBLESHOOTING.md#401-invalid_username-or-401-incorrect_password-on-wordpress-auth)).

## 4. Known environmental quirks — don't "fix" these away

These look like they should be simplified but are load-bearing workarounds for
this specific server. Full context in [DECISIONS.md](DECISIONS.md):

- `BROWSER_HEADERS` (spoofed browser User-Agent) on every WooCommerce/WordPress
  request — removing it reintroduces a `406` from ModSecurity.
- `Content-Type: application/octet-stream` (not the real image MIME type) on
  media uploads — using the real `image/webp` content type triggers a `406`.
- `allow_redirects=False` + explicit raise on 301/302 in `publish_to_woocommerce`
  — this exists specifically to prevent a silent POST→GET downgrade that once
  caused the API to return the wrong product.
- The keyphrase density formula is `occurrences / total_words * 100`, **not**
  weighted by keyphrase word count — the weighted version was tried, was wrong,
  and rejected valid, natural-sounding copy.

## 5. Adding a new SEO validation rule

1. Add the check to `validator_node` in `app/graph.py`, following the existing
   pattern: compute a value from the parsed `soup`/`text`, append a specific,
   actionable message to `errors` on failure (the message is fed verbatim back
   to Gemini as retry feedback, so make it instructive, not just "X failed").
2. If the rule depends on the *generated content*, it belongs in the retry loop
   (`validator_node`) so the writer can fix it. If it depends only on the
   *input* (like keyphrase length), put it in `main.py` as a pre-flight check
   instead — see [DECISIONS.md #6](DECISIONS.md#6-two-seo-checks-moved-out-of-the-writervalidator-retry-loop)
   for why this distinction matters (retrying can't fix an input-level problem).
3. Update `app/prompt.py` so Gemini is told about the new rule up front —
   otherwise every first attempt will predictably fail it.
4. Test the new check against a hand-built `state` dict first (no side effects),
   then against one real Gemini call before running it through a full publish.

## 6. Code style already established in this repo

- No unnecessary comments — only where a decision is non-obvious (see the
  ModSecurity workarounds for the standard this repo holds itself to).
- No speculative abstraction — e.g. the model fallback chain is a flat list,
  not a config system, because there are only three models.
- Prefer extending existing modules (`woocommerce.py`, `graph.py`) over adding
  new files, unless the responsibility is genuinely separate (e.g.
  `wordpress_media.py` is its own file because it uses a completely different
  auth mechanism from `woocommerce.py`, not because of file-size preferences).

## Related

- [DECISIONS.md](DECISIONS.md) — why each of the above is true
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — symptom → fix index
- [PROJECT.md](PROJECT.md) — architecture overview
