(() => {
  "use strict";
  const state = { base: "http://127.0.0.1:8080/api/v1", token: "dev:platform", box: null, identities: [], lastOperation: null };
  const $ = (id) => document.getElementById(id);
  const output = (value) => { $("results").textContent = JSON.stringify(value, null, 2); };
  const setError = (error) => {
    const safe = error && typeof error === "object" ? error : {};
    $("error-text").textContent = safe.detail || safe.title || "The request failed.";
    $("error-summary").hidden = false; $("error-summary").focus();
    output({ code: safe.code || "request_failed", detail: safe.detail || "The request failed.", requestId: safe.requestId || null, fieldErrors: safe.fieldErrors || [] });
  };
  const clearError = () => { $("error-summary").hidden = true; };
  const headers = (mutating = false) => {
    const result = { Authorization: `Bearer ${state.token}`, "Content-Type": "application/json" };
    if (mutating) result["Idempotency-Key"] = `ui-${crypto.randomUUID()}`;
    return result;
  };
  async function request(path, options = {}) {
    const response = await fetch(`${state.base}${path}`, options);
    const value = response.status === 204 ? {} : await response.json();
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
    if (state.box) { $("access-status").textContent = state.identities.length ? `${state.identities.length} identity reference(s) available.` : "No identity loaded."; }
  }
  $("connection-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    clearError(); state.base = $("api-base").value.replace(/\/$/, "");
    state.token = $("token").value;
    try { await loadBoxes(); } catch (error) { $("connection-status").textContent = "Connection failed."; setError(error); }
  });
  $("box-select").addEventListener("change", (event) => { state.box = event.target.value || null; state.identities = []; $("access-status").textContent = "No identity loaded."; });
  $("box-form").addEventListener("submit", async (event) => {
    event.preventDefault(); clearError();
    try { await request("/boxes", { method: "POST", headers: headers(true), body: JSON.stringify({ name: $("box-name").value, kind: "test" }) }); $("box-name").value = ""; await loadBoxes(); } catch (error) { setError(error); }
  });
  $("message-form").addEventListener("submit", async (event) => {
    event.preventDefault(); clearError();
    if (!state.box) { setError({ detail: "Select a synthetic box first." }); return; }
    try {
      const payload = { boxId: state.box, subject: $("subject").value }; if ($("target-box").value.trim()) payload.targetBoxId = $("target-box").value.trim();
      const message = await request("/messages", { method: "POST", headers: headers(true), body: JSON.stringify(payload) });
      const bytes = new TextEncoder().encode($("attachment").value);
      const base64 = btoa(String.fromCharCode(...bytes));
      await request(`/messages/${message.id}/attachments`, { method: "POST", headers: headers(true), body: JSON.stringify({ filename: "ui.txt", mediaType: "text/plain", contentBase64: base64, byteLength: bytes.length }) });
      const operation = await request(`/messages/${message.id}/submit`, { method: "POST", headers: headers(true), body: JSON.stringify({}) });
      state.lastOperation = operation.operationId; output({ message, operation, note: "Run the local synthetic worker to project delivery and receipt evidence." }); $("record-status").textContent = `Operation ${operation.operationId} queued.`;
    } catch (error) { setError(error); }
  });
  $("refresh").addEventListener("click", async () => {
    if (!state.box) { setError({ detail: "Select a synthetic box first." }); return; }
    try { const query = new URLSearchParams({ boxId: state.box, limit: "50" }); if ($("search-text").value.trim()) query.set("q", $("search-text").value.trim()); const result = { messages: await request(`/messages?${query}`), audit: await request(`/audit/events?boxId=${encodeURIComponent(state.box)}&limit=50`) }; if (state.lastOperation) result.operation = await request(`/operations/${state.lastOperation}`); output(result); $("record-status").textContent = "Records refreshed."; } catch (error) { setError(error); }
  });
  $("identity-form").addEventListener("submit", async (event) => { event.preventDefault(); clearError(); try { if (!state.box) throw { detail: "Select a synthetic box first." }; const identity = await request(`/boxes/${state.box}/identities`, { method: "POST", headers: headers(true), body: JSON.stringify({ subject: $("identity-subject").value, displayName: $("identity-name").value }) }); state.identities.push(identity.id); const option = new Option(identity.displayName, identity.id); $("identity-select").add(option); $("identity-select").value = identity.id; $("access-status").textContent = `Identity ${identity.id} created.`; } catch (error) { setError(error); } });
  $("membership-form").addEventListener("submit", async (event) => { event.preventDefault(); clearError(); try { if (!state.box) throw { detail: "Select a synthetic box first." }; const identity = $("identity-select").value; if (!identity) throw { detail: "Create or select an identity first." }; const result = await request(`/boxes/${state.box}/members/${identity}`, { method: "PUT", headers: headers(true), body: JSON.stringify({ role: $("role-select").value }) }); $("access-status").textContent = `Membership assigned: ${result.role}.`; } catch (error) { setError(error); } });
  $("search-form").addEventListener("submit", async (event) => { event.preventDefault(); $("refresh").click(); });
  $("operation-refresh").addEventListener("click", async () => { clearError(); try { if (!state.lastOperation) throw { detail: "Submit a message before refreshing an operation." }; const operation = await request(`/operations/${state.lastOperation}`); output({ operation, lifecycle: await request(`/messages/${operation.messageId}/events`) }); } catch (error) { setError(error); } });
  $("export").addEventListener("click", async () => { clearError(); try { if (!state.box) throw { detail: "Select a synthetic box first." }; const created = await request("/exports", { method: "POST", headers: headers(true), body: JSON.stringify({ boxId: state.box, format: "jsonl" }) }); output({ export: await request(`/exports/${created.id}`), note: "Manifest and receipt references are synthetic evidence." }); } catch (error) { setError(error); } });
  $("profile-form").addEventListener("submit", async (event) => { event.preventDefault(); clearError(); try {
    const trust = await request("/trust-profiles", { method: "POST", headers: headers(true), body: JSON.stringify({ name: $("trust-name").value, version: "1", anchorFingerprints: [$("trust-anchor").value], hostnames: [$("endpoint-host").value] }) });
    const endpointHost = $("endpoint-host").value;
    const endpoint = await request("/endpoint-profiles", { method: "POST", headers: headers(true), body: JSON.stringify({ name: "ui-synthetic-endpoint", scheme: "https", hostname: endpointHost, allowList: [endpointHost] }) });
    output({ trustProfile: trust, endpointProfile: endpoint });
  } catch (error) { setError(error); } });
  $("hold-form").addEventListener("submit", async (event) => { event.preventDefault(); clearError(); try { if (!state.box) throw { detail: "Select a synthetic box first." }; output(await request("/retention/legal-holds", { method: "POST", headers: headers(true), body: JSON.stringify({ boxId: state.box, resourceType: "message", resourceId: $("hold-resource").value, reason: $("hold-reason").value }) })); } catch (error) { setError(error); } });
  $("retention-form").addEventListener("submit", async (event) => { event.preventDefault(); clearError(); try { if (!state.box) throw { detail: "Select a synthetic box first." }; const tombstone = await request("/retention/deletion-requests", { method: "POST", headers: headers(true), body: JSON.stringify({ boxId: state.box, resourceType: "message", resourceId: $("retention-resource").value }) }); const result = { tombstone }; if ($("retention-export").value.trim()) result.restore = await request("/retention/restore", { method: "POST", headers: headers(true), body: JSON.stringify({ boxId: state.box, exportId: $("retention-export").value.trim(), namespace: "ui-restore" }) }); output(result); } catch (error) { setError(error); } });
  $("receipt-form").addEventListener("submit", async (event) => { event.preventDefault(); clearError(); try { output(await request(`/messages/${encodeURIComponent($("receipt-message").value)}/receipts/${encodeURIComponent($("receipt-id").value)}`)); } catch (error) { setError(error); } });
  $("health").addEventListener("click", async () => { clearError(); try { output({ status: "ok", api: await request("") }); } catch (error) { setError(error); } });
})();
