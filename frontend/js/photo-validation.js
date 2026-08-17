// ---------------------------------------------------------------------
// Client-side product photo pre-validation (advisory only -- the
// server's _validate_product_image is the real enforcement point)
// ---------------------------------------------------------------------

const REQUIRED_WIDTH = 1000;
const REQUIRED_HEIGHT = 1000;
const MAX_PHOTO_BYTES = 35 * 1024;

const ROW_BASE = "flex items-center gap-2 text-[0.82rem] px-[0.6rem] py-[0.4rem] rounded-md";
const ROW_OK = "bg-[#ecfdf3] dark:bg-[#0f2a1a] text-green-700 dark:text-green-400";
const ROW_BAD = "bg-red-50 dark:bg-[#2a1414] text-red-700 dark:text-red-400";

function readHeaderBytes(file, n) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(new Uint8Array(reader.result));
    reader.onerror = reject;
    reader.readAsArrayBuffer(file.slice(0, n));
  });
}

function getImageDimensions(file) {
  return new Promise((resolve, reject) => {
    const decodeWithBitmap =
      typeof createImageBitmap === "function"
        ? createImageBitmap(file).then((bmp) => {
            const dims = { width: bmp.width, height: bmp.height };
            bmp.close && bmp.close();
            return dims;
          })
        : Promise.reject();

    decodeWithBitmap.then(resolve, () => {
      const url = URL.createObjectURL(file);
      const img = new Image();
      img.onload = () => {
        resolve({ width: img.naturalWidth, height: img.naturalHeight });
        URL.revokeObjectURL(url);
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error("could not decode image"));
      };
      img.src = url;
    });
  });
}

export async function validatePhoto(file) {
  const header = await readHeaderBytes(file, 16).catch(() => null);
  if (!header) return { ok: false, reason: "could not read file." };

  const isRiff =
    header[0] === 0x52 &&
    header[1] === 0x49 &&
    header[2] === 0x46 &&
    header[3] === 0x46;
  const isWebp =
    header[8] === 0x57 &&
    header[9] === 0x45 &&
    header[10] === 0x42 &&
    header[11] === 0x50;
  if (!isRiff || !isWebp) {
    return {
      ok: false,
      reason: "not a WebP file. Only WebP product photos may be uploaded.",
    };
  }
  if (file.size >= MAX_PHOTO_BYTES) {
    return {
      ok: false,
      reason: `${file.size} bytes exceeds the ${MAX_PHOTO_BYTES}-byte (35KB) limit.`,
    };
  }
  try {
    const { width, height } = await getImageDimensions(file);
    if (width !== REQUIRED_WIDTH || height !== REQUIRED_HEIGHT) {
      return {
        ok: false,
        reason: `dimensions ${width}x${height} do not match the required ${REQUIRED_WIDTH}x${REQUIRED_HEIGHT}.`,
      };
    }
  } catch {
    return { ok: false, reason: "could not determine image dimensions." };
  }
  return { ok: true };
}

async function renderPhotoStatus(input, statusContainer) {
  statusContainer.innerHTML = "";
  for (const file of input.files) {
    const row = document.createElement("div");
    row.className = ROW_BASE;
    row.innerHTML = `<span class="font-bold">…</span><span>${file.name}</span>`;
    statusContainer.appendChild(row);

    const result = await validatePhoto(file);
    row.className = `${ROW_BASE} ${result.ok ? ROW_OK : ROW_BAD}`;
    row.innerHTML = result.ok
      ? `<span class="font-bold">✓</span><span>${file.name} — looks good</span>`
      : `<span class="font-bold">✗</span><span>${file.name} — ${result.reason}</span>`;
  }
}

export function initPhotoValidation({ input, statusContainer }) {
  input.addEventListener("change", () => renderPhotoStatus(input, statusContainer));
}
