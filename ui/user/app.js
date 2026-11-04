(() => {
  "use strict";

  const state = { base: "/api/v1", token: "", session: null, box: null, folder: "inbox", messages: [], retry: null };
  const $ = (id) => document.getElementById(id);
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[character]));
  const showError = (error) => { $("error-text").textContent = error?.detail || error?.title || "The request failed."; $("error").hidden = false; $("error").focus(); };
  const clearError = () => { $("error").hidden = true; };
  const headers = (mutating) => { const result = { Authorization: `Bearer ${state.token}`, "Content-Type": "application/json" }; if (mutating) result["Idempotency-Key"] = `user-${crypto.randomUUID()}`; return result; };
  const api = async (path, options = {}) => { const requestOptions = { ...options, headers: { ...headers(false), ...(options.headers || {}) } }; const response = await fetch(state.base + path, requestOptions); const value = response.status === 204 ? {} : await response.json(); if (!response.ok) throw value; return value; };

  async function login() {
    clearError(); state.base = $("api-base").value.replace(/\/$/, ""); state.token = $("token").value;
    const session = await api("/session"); const boxes = await api("/boxes"); state.session = session; state.box = session.tenant || boxes.items[0]?.id;
    sessionStorage.setItem("ag-user-session", JSON.stringify({ base: state.base, token: state.token })); $("login-panel").hidden = true; $("workspace").hidden = false; $("session-label").textContent = `Signed in as ${session.identity?.displayName || session.subject}`;
    const select = $("box-select"); select.replaceChildren(...boxes.items.map((box) => new Option(`${box.name} (${box.id})`, box.id))); select.value = state.box; await refresh();
  }
  function isFolder(message) { if (state.folder === "all") return true; const outgoing = message.senderIdentityId === state.session?.identity?.id; return state.folder === "outbox" ? outgoing : !outgoing; }
  function render() {
    const list = $("message-list"); list.replaceChildren(); const items = state.messages.filter(isFolder); if (!items.length) { list.textContent = "No messages match this view."; return; }
    for (const message of items) { const article = document.createElement("article"); article.className = `message-card${message.readAt ? "" : " unread"}`; article.innerHTML = `<div><h3>${escapeHtml(message.subject)}</h3><p>${escapeHtml(message.status)} · ${escapeHtml(message.createdAt)} · ${message.readAt ? "read" : "unread"}</p></div><button type="button" data-message-id="${escapeHtml(message.id)}">Open</button>`; list.append(article); }
  }
  async function refresh() {
    const query = new URLSearchParams({ boxId: state.box, limit: "100" }); if ($("query").value.trim()) query.set("q", $("query").value.trim()); if ($("status-filter").value) query.set("status", $("status-filter").value);
    state.messages = (await api(`/messages?${query}`)).items; render(); $("list-status").textContent = `${state.messages.length} message(s) loaded.`;
  }
  async function detail(id) {
    clearError(); const message = await api(`/messages/${id}`); const [events, attachments] = await Promise.all([api(`/messages/${id}/events`), api(`/messages/${id}/attachments`)]);
    if (!message.readAt) await api(`/messages/${id}/read`, { method: "PATCH", headers: headers(true), body: JSON.stringify({ read: true }) }); $("detail-panel").hidden = false;
    $("detail").innerHTML = `<dl class="detail-row"><dt>Subject</dt><dd>${escapeHtml(message.subject)}</dd></dl><dl class="detail-row"><dt>Status</dt><dd>${escapeHtml(message.status)}</dd></dl><dl class="detail-row"><dt>Lifecycle</dt><dd>${events.items.map((event) => `${escapeHtml(event.eventType)} (${escapeHtml(event.sourceCode || "local")})`).join(" → ")}</dd></dl>`;
    const list = document.createElement("ul"); list.className = "attachment-list";
    for (const attachment of attachments.items) { const item = document.createElement("li"); const button = document.createElement("button"); button.className = "secondary"; button.type = "button"; button.textContent = `Download ${attachment.filename} (${attachment.byteLength} bytes)`; button.onclick = () => download(id, attachment); item.append(button, document.createTextNode(` · ${attachment.contentDigest}`)); list.append(item); }
    $("detail").append(list); await refresh();
  }
  async function download(messageId, attachment) {
    const value = await api(`/messages/${messageId}/attachments/${attachment.id}`); const raw = atob(value.contentBase64); const bytes = Uint8Array.from(raw, (character) => character.charCodeAt(0)); const url = URL.createObjectURL(new Blob([bytes], { type: value.mediaType })); const link = document.createElement("a"); link.href = url; link.download = value.filename; link.click(); URL.revokeObjectURL(url);
  }
  async function compose(event) {
    event.preventDefault(); try {
      const file = $("attachment").files[0]; const message = await api("/messages", { method: "POST", headers: headers(true), body: JSON.stringify({ boxId: state.box, subject: $("subject").value, targetBoxId: $("target-box").value, senderIdentityId: state.session.identity.id }) });
      if (file) { const bytes = new Uint8Array(await file.arrayBuffer()); let raw = ""; bytes.forEach((byte) => { raw += String.fromCharCode(byte); }); await api(`/messages/${message.id}/attachments`, { method: "POST", headers: headers(true), body: JSON.stringify({ filename: file.name, mediaType: file.type || "application/octet-stream", contentBase64: btoa(raw), byteLength: bytes.length }) }); }
      const operation = await api(`/messages/${message.id}/submit`, { method: "POST", headers: headers(true), body: JSON.stringify({}) }); $("compose-status").textContent = `Accepted as ${operation.operationId}; queued for synthetic delivery.`; $("compose-form").reset(); await refresh();
    } catch (error) { state.retry = () => compose(event); showError(error); }
  }
  $("login-form").onsubmit = (event) => { event.preventDefault(); login().catch(showError); }; $("sign-out").onclick = () => { sessionStorage.removeItem("ag-user-session"); location.reload(); }; $("refresh").onclick = () => refresh().catch(showError); $("retry").onclick = () => (state.retry ? state.retry() : refresh().catch(showError)); $("filter-form").onsubmit = (event) => { event.preventDefault(); refresh().catch(showError); }; $("box-select").onchange = (event) => { state.box = event.target.value; refresh().catch(showError); }; $("compose-form").onsubmit = compose;
  $("message-list").onclick = (event) => { const button = event.target.closest("button[data-message-id]"); if (button) detail(button.dataset.messageId).catch(showError); }; $("detail-close").onclick = () => { $("detail-panel").hidden = true; }; $("compose-open").onclick = () => { $("compose-panel").hidden = false; $("subject").focus(); }; $("compose-close").onclick = () => { $("compose-panel").hidden = true; };
  $("export").onclick = async () => { try { const created = await api("/exports", { method: "POST", headers: headers(true), body: JSON.stringify({ boxId: state.box, format: "jsonl" }) }); const value = await api(`/exports/${created.id}`); const link = $("export-download"); link.href = URL.createObjectURL(new Blob([JSON.stringify(value.result, null, 2)], { type: "application/json" })); link.hidden = false; $("export-status").textContent = `Export ${created.id} verified by ${value.manifestDigest}.`; } catch (error) { showError(error); } };
  document.querySelectorAll(".tab").forEach((button) => button.onclick = () => { document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active")); button.classList.add("active"); state.folder = button.dataset.folder; render(); });
  try { const value = JSON.parse(sessionStorage.getItem("ag-user-session") || "null"); if (value) { $("api-base").value = value.base; $("token").value = value.token; login().catch(() => {}); } } catch (_) { /* Show the sign-in form for malformed session storage. */ }
})();
