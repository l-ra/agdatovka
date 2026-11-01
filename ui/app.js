(() => {
  "use strict";
  const state = { base: "http://127.0.0.1:8080/api/v1", token: "dev:platform", box: null };
  const $ = (id) => document.getElementById(id);
  const output = (value) => { $("results").textContent = JSON.stringify(value, null, 2); };
  const headers = (mutating = false) => {
    const result = { Authorization: `Bearer ${state.token}`, "Content-Type": "application/json" };
    if (mutating) result["Idempotency-Key"] = `ui-${crypto.randomUUID()}`;
    return result;
  };
  async function request(path, options = {}) {
    const response = await fetch(`${state.base}${path}`, options);
    const value = await response.json();
    if (!response.ok) throw value;
    return value;
  }
  async function loadBoxes() {
    const page = await request("/boxes");
    const select = $("box-select");
    select.replaceChildren(...page.items.map((box) => new Option(`${box.name} (${box.id})`, box.id)));
    if (state.box && page.items.some((box) => box.id === state.box)) select.value = state.box;
    state.box = select.value || null;
    $("connection-status").textContent = `Connected; ${page.items.length} synthetic box(es) loaded.`;
  }
  $("connection-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    state.base = $("api-base").value.replace(/\/$/, "");
    state.token = $("token").value;
    try { await loadBoxes(); } catch (error) { $("connection-status").textContent = error.detail || "Connection failed."; output(error); }
  });
  $("box-select").addEventListener("change", (event) => { state.box = event.target.value || null; });
  $("box-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try { await request("/boxes", { method: "POST", headers: headers(true), body: JSON.stringify({ name: $("box-name").value, kind: "test" }) }); await loadBoxes(); } catch (error) { output(error); }
  });
  $("message-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!state.box) { output({ detail: "Select a synthetic box first." }); return; }
    try {
      const message = await request("/messages", { method: "POST", headers: headers(true), body: JSON.stringify({ boxId: state.box, subject: $("subject").value }) });
      const bytes = new TextEncoder().encode($("attachment").value);
      const base64 = btoa(String.fromCharCode(...bytes));
      await request(`/messages/${message.id}/attachments`, { method: "POST", headers: headers(true), body: JSON.stringify({ filename: "ui.txt", mediaType: "text/plain", contentBase64: base64, byteLength: bytes.length }) });
      const operation = await request(`/messages/${message.id}/submit`, { method: "POST", headers: headers(true), body: JSON.stringify({}) });
      output({ message, operation, note: "Run the synthetic worker from the test harness to project delivery and receipt evidence." });
    } catch (error) { output(error); }
  });
  $("refresh").addEventListener("click", async () => {
    if (!state.box) { output({ detail: "Select a synthetic box first." }); return; }
    try { output({ messages: await request(`/messages/search?boxId=${encodeURIComponent(state.box)}`), audit: await request(`/audit/events?boxId=${encodeURIComponent(state.box)}`) }); } catch (error) { output(error); }
  });
})();
