const $ = (id) => document.getElementById(id);
const PAGE = 10;
let ws, ctx, stream, node, startedAt = 0, recording = false;
let offset = 0, total = 0, query = "", lastError = "";

/* ---------- live transcription ---------- */
async function start() {
  stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true } });
  ctx = new AudioContext();
  await ctx.audioWorklet.addModule("/static/worklet.js");
  const src = ctx.createMediaStreamSource(stream);
  node = new AudioWorkletNode(ctx, "pcm-processor");
  src.connect(node);

  lastError = "";
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws/transcribe?lang=${encodeURIComponent($("lang").value)}`);
  ws.onopen = () => {
    node.port.onmessage = (e) => ws.readyState === 1 && ws.send(e.data);
    startedAt = Date.now();
    recording = true;
    setUI();
  };
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.type === "partial" || m.type === "final") $("live").value = m.text;
    if (m.type === "error") { lastError = "Error: " + m.message; $("status").textContent = lastError; }
    if (m.type === "final") {
      $("save").disabled = !m.text;
      if (!m.text && !lastError) lastError = "No speech recognized. Speak louder or check the mic.";
    }
  };
  ws.onclose = () => { cleanup(); setUI(); };
}

function stop() {
  if (ws && ws.readyState === 1) ws.send("stop");
  cleanup();
  $("status").textContent = "Finalizing...";
}

function cleanup() {
  recording = false;
  stream && stream.getTracks().forEach((t) => t.stop());
  ctx && ctx.close();
  stream = ctx = null;
}

async function loadLanguages() {
  let data = { default: "hi-IN", items: [{ code: "hi-IN", label: "Hindi (mixed with English)" }] };
  try { data = await api("/api/languages"); } catch (e) { /* keep fallback */ }
  $("lang").innerHTML = data.items.map((l) => `<option value="${l.code}">${esc(l.label)}</option>`).join("");
  $("lang").value = data.default;
}

function setUI() {
  $("lang").disabled = recording;
  $("toggle").textContent = recording ? "⏹ Stop" : "🎤 Start";
  $("toggle").classList.toggle("rec", recording);
  $("status").textContent = recording ? "Listening..." : (lastError || "Idle");
  $("save").disabled = recording || !$("live").value.trim();
}

$("toggle").onclick = () => (recording ? stop() : start().catch((e) => ($("status").textContent = e.message)));
$("live").oninput = setUI;
$("clear").onclick = () => { $("live").value = ""; setUI(); };
$("save").onclick = async () => {
  const text = $("live").value.trim();
  if (!text) return;
  await api("/api/transcripts", "POST", { text, duration_sec: (Date.now() - startedAt) / 1000 });
  $("live").value = ""; setUI(); offset = 0; load();
};

/* ---------- dashboard (CRUD) ---------- */
async function api(url, method = "GET", body) {
  const r = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(await r.text());
  return r.status === 204 ? null : r.json();
}

const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

async function load() {
  const p = new URLSearchParams({ limit: PAGE, offset, ...(query && { q: query }) });
  const { items, total: t } = await api("/api/transcripts?" + p);
  total = t;
  $("rows").innerHTML = items.map((i) => `
    <tr data-id="${i.id}">
      <td class="txt">${esc(i.text)}</td>
      <td>${new Date(i.created_at).toLocaleString()}</td>
      <td class="actions">
        <button data-act="edit">Edit</button>
        <button data-act="del" class="ghost">Delete</button>
      </td>
    </tr>`).join("") || `<tr><td colspan="3" class="muted">No transcripts yet.</td></tr>`;
  $("page").textContent = total ? `${offset + 1}-${Math.min(offset + PAGE, total)} of ${total}` : "";
  $("prev").disabled = offset === 0;
  $("next").disabled = offset + PAGE >= total;
}

$("rows").onclick = async (e) => {
  const btn = e.target.closest("button");
  if (!btn) return;
  const tr = btn.closest("tr"), id = tr.dataset.id;
  if (btn.dataset.act === "del") {
    if (confirm("Delete this transcript?")) { await api(`/api/transcripts/${id}`, "DELETE"); load(); }
  } else if (btn.dataset.act === "edit") {
    const td = tr.querySelector(".txt");
    td.innerHTML = `<textarea>${esc(td.textContent)}</textarea>`;
    btn.dataset.act = "save"; btn.textContent = "Save";
  } else if (btn.dataset.act === "save") {
    const text = tr.querySelector("textarea").value.trim();
    if (text) { await api(`/api/transcripts/${id}`, "PUT", { text }); load(); }
  }
};

let timer;
$("search").oninput = (e) => { clearTimeout(timer); timer = setTimeout(() => { query = e.target.value; offset = 0; load(); }, 300); };
$("prev").onclick = () => { offset = Math.max(0, offset - PAGE); load(); };
$("next").onclick = () => { offset += PAGE; load(); };

loadLanguages();
load();
