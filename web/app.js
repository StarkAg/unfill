const $ = (id) => document.getElementById(id);

const drop = $("drop");
const fileInput = $("file");
const statusBox = $("status");
const statusText = $("statusText");
const errorBox = $("error");
const result = $("result");
const beforeImg = $("before");
const afterImg = $("after");
const compare = $("compare");
const beforeWrap = $("beforeWrap");
const handle = $("handle");
const growInput = $("grow");

let objectUrls = [];

const revoke = () => {
  objectUrls.forEach(URL.revokeObjectURL);
  objectUrls = [];
};

const show = (el, on) => { el.hidden = !on; };

growInput.addEventListener("input", () => { $("growOut").value = growInput.value; });

// ---- pick a file -------------------------------------------------------

drop.addEventListener("click", () => fileInput.click());
$("browse").addEventListener("click", (e) => { e.stopPropagation(); fileInput.click(); });
fileInput.addEventListener("change", () => fileInput.files[0] && run(fileInput.files[0]));

["dragenter", "dragover"].forEach((ev) =>
  drop.addEventListener(ev, (e) => {
    e.preventDefault();
    drop.classList.add("over");
  })
);

["dragleave", "drop"].forEach((ev) =>
  drop.addEventListener(ev, (e) => {
    e.preventDefault();
    drop.classList.remove("over");
  })
);

drop.addEventListener("drop", (e) => {
  const f = e.dataTransfer.files[0];
  if (f) run(f);
});

$("again").addEventListener("click", () => {
  fileInput.value = "";
  show(result, false);
  show(drop, true);
});

// ---- the actual call ---------------------------------------------------

async function run(file) {
  if (!file.type.startsWith("image/")) {
    return fail("That doesn't look like an image.");
  }

  revoke();
  show(errorBox, false);
  show(result, false);
  show(drop, false);
  show(statusBox, true);
  statusText.textContent = "Detecting ink and erasing…";

  const body = new FormData();
  body.append("file", file);
  body.append("whiten_paper", $("whiten").checked);
  body.append("grow", growInput.value);

  try {
    const res = await fetch("/api/unfill", { method: "POST", body });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || `Server returned ${res.status}`);
    }

    const coverage = res.headers.get("X-Ink-Coverage");
    const blob = await res.blob();

    const beforeUrl = URL.createObjectURL(file);
    const afterUrl = URL.createObjectURL(blob);
    objectUrls.push(beforeUrl, afterUrl);

    beforeImg.src = beforeUrl;
    afterImg.src = afterUrl;
    $("download").href = afterUrl;
    $("download").download = file.name.replace(/\.[^.]+$/, "") + "_blank.png";
    $("meta").textContent = `Erased ${coverage}% of the page. Saved at 300 DPI.`;

    await afterImg.decode().catch(() => {});
    setSplit(0.5);

    show(statusBox, false);
    show(result, true);
  } catch (err) {
    show(statusBox, false);
    show(drop, true);
    fail(err.message);
  }
}

function fail(msg) {
  errorBox.textContent = msg;
  show(errorBox, true);
}

// ---- before/after slider ----------------------------------------------

function setSplit(fraction) {
  const f = Math.max(0, Math.min(1, fraction));
  const width = compare.clientWidth;
  beforeWrap.style.width = `${f * 100}%`;
  // The clipped image must stay at full container width, or it squashes.
  beforeImg.style.width = `${width}px`;
  handle.style.left = `${f * 100}%`;
}

let dragging = false;
const pointToFraction = (clientX) => {
  const r = compare.getBoundingClientRect();
  return (clientX - r.left) / r.width;
};

compare.addEventListener("pointerdown", (e) => {
  dragging = true;
  compare.setPointerCapture(e.pointerId);
  setSplit(pointToFraction(e.clientX));
});

compare.addEventListener("pointermove", (e) => {
  if (dragging) setSplit(pointToFraction(e.clientX));
});

compare.addEventListener("pointerup", (e) => {
  dragging = false;
  compare.releasePointerCapture(e.pointerId);
});

window.addEventListener("resize", () => {
  if (!result.hidden) {
    setSplit(parseFloat(beforeWrap.style.width) / 100 || 0.5);
  }
});
