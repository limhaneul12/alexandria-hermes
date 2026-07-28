"use strict";

const elements = {
  mcpEndpoint: document.querySelector("#mcp-endpoint"),
  mcpMode: document.querySelector("#mcp-mode"),
  mcpIssuer: document.querySelector("#mcp-issuer"),
  mcpNotice: document.querySelector("#mcp-notice"),
  copyMcpEndpoint: document.querySelector("#copy-mcp-endpoint"),
  generatePairingCode: document.querySelector("#generate-pairing-code"),
  pairingPanel: document.querySelector("#pairing-panel"),
  pairingCode: document.querySelector("#pairing-code"),
  pairingExpiry: document.querySelector("#pairing-expiry"),
  mcpMessage: document.querySelector("#mcp-message"),
  refreshMcpClients: document.querySelector("#refresh-mcp-clients"),
  mcpClientList: document.querySelector("#mcp-client-list"),
};

function setMessage(element, text, isError = false) {
  element.textContent = text;
  element.className = isError ? "message error" : "message";
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail || payload.message || detail;
    } catch {
      // Keep the HTTP status when an admin-only page returns non-JSON.
    }
    throw new Error(detail);
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

async function loadMcpStatus() {
  try {
    const status = await api("/connect/status");
    elements.mcpEndpoint.textContent = status.mcp_endpoint;
    elements.mcpMode.textContent = status.mcp_auth_mode;
    elements.mcpIssuer.textContent = status.mcp_oauth_issuer || "—";
    if (status.mcp_oauth_enabled) {
      elements.mcpNotice.textContent = "MCP OAuth가 활성화되어 있습니다. Endpoint를 클라이언트에 등록하고 필요 시 일회용 페어링 코드를 생성하세요.";
      elements.mcpNotice.className = "notice ok";
      elements.generatePairingCode.hidden = false;
    } else {
      elements.mcpNotice.textContent = "MCP local_oauth2 모드가 아닙니다. 관리 기능은 비활성화됩니다.";
      elements.mcpNotice.className = "notice warn";
      elements.generatePairingCode.hidden = true;
    }
    if (!status.local_only) {
      elements.mcpNotice.textContent = "관리 페이지는 localhost에서만 사용할 수 있습니다.";
      elements.mcpNotice.className = "notice warn";
    }
  } catch (error) {
    elements.mcpNotice.textContent = "MCP 상태를 불러오지 못했습니다.";
    elements.mcpNotice.className = "notice warn";
    setMessage(elements.mcpMessage, error.message, true);
  }
}

async function loadMcpClients() {
  try {
    const payload = await api("/connect/mcp/clients");
    renderMcpClients(payload.clients || []);
  } catch (error) {
    elements.mcpClientList.textContent = "MCP OAuth 클라이언트 목록을 불러오지 못했습니다.";
    setMessage(elements.mcpMessage, error.message, true);
  }
}

function renderMcpClients(clients) {
  elements.mcpClientList.replaceChildren();
  if (clients.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "등록된 OAuth MCP 클라이언트가 없습니다.";
    elements.mcpClientList.append(empty);
    return;
  }
  for (const client of clients) {
    elements.mcpClientList.append(mcpClientRow(client));
  }
}

function mcpClientRow(client) {
  const row = document.createElement("article");
  row.className = "client-row wide";

  const title = document.createElement("div");
  const name = document.createElement("strong");
  name.textContent = client.client_name || "이름 없는 MCP 클라이언트";
  const identifier = document.createElement("small");
  identifier.textContent = client.client_id;
  title.append(name, identifier);

  const metadata = document.createElement("div");
  metadata.className = "client-metadata";
  metadata.append(
    clientMetric("Status", client.status),
    clientMetric("Scopes", (client.scopes || []).join(" ") || "scope 없음"),
    clientMetric("Refresh 만료", client.refresh_token_expires_at || "—"),
    clientMetric("Access 만료", client.access_token_expires_at || "—"),
  );

  const controls = document.createElement("div");
  controls.className = "client-controls";
  const statusPill = document.createElement("span");
  statusPill.className = client.connected ? "pill ok" : "pill warn";
  statusPill.textContent = client.status;
  controls.append(statusPill);

  const extend = document.createElement("button");
  extend.className = "secondary compact";
  extend.type = "button";
  extend.textContent = "연장";
  extend.disabled = !client.supports_extension;
  extend.dataset.action = "extend";
  extend.dataset.clientId = client.client_id;
  controls.append(extend);

  const disconnect = document.createElement("button");
  disconnect.className = "ghost compact";
  disconnect.type = "button";
  disconnect.textContent = "연결 끊기";
  disconnect.disabled = !client.supports_disconnect;
  disconnect.dataset.action = "disconnect";
  disconnect.dataset.clientId = client.client_id;
  controls.append(disconnect);

  row.append(title, metadata, controls);
  return row;
}

function clientMetric(label, value) {
  const item = document.createElement("span");
  const key = document.createElement("small");
  key.textContent = label;
  const text = document.createElement("b");
  text.textContent = value;
  item.append(key, text);
  return item;
}

async function manageMcpClient(action, clientId) {
  const verb = action === "extend" ? "연장" : "연결 해제";
  setMessage(elements.mcpMessage, `MCP 클라이언트 ${verb} 중…`);
  try {
    await api(
      `/connect/mcp/clients/${encodeURIComponent(clientId)}/${action}`,
      { method: "POST" },
    );
    await loadMcpClients();
    setMessage(elements.mcpMessage, `MCP 클라이언트 ${verb}가 완료되었습니다.`);
  } catch (error) {
    setMessage(elements.mcpMessage, error.message, true);
  }
}

async function copyMcpEndpoint() {
  try {
    await navigator.clipboard.writeText(elements.mcpEndpoint.textContent);
    setMessage(elements.mcpMessage, "MCP Endpoint를 복사했습니다.");
  } catch {
    setMessage(elements.mcpMessage, "클립보드 복사에 실패했습니다.", true);
  }
}

async function generatePairingCode() {
  elements.generatePairingCode.disabled = true;
  try {
    const pairing = await api("/connect/mcp/pairing-code", { method: "POST" });
    elements.pairingCode.textContent = pairing.code;
    elements.pairingExpiry.textContent = `만료: ${pairing.expires_at}`;
    elements.pairingPanel.hidden = false;
    let copied = true;
    try {
      await navigator.clipboard.writeText(pairing.code);
    } catch {
      copied = false;
    }
    setMessage(
      elements.mcpMessage,
      copied
        ? "일회용 코드를 생성하고 클립보드에 복사했습니다."
        : "일회용 코드를 생성했습니다. 승인 페이지에 직접 입력하세요.",
    );
  } catch (error) {
    setMessage(elements.mcpMessage, error.message, true);
  } finally {
    elements.generatePairingCode.disabled = false;
  }
}

elements.copyMcpEndpoint.addEventListener("click", copyMcpEndpoint);
elements.generatePairingCode.addEventListener("click", generatePairingCode);
elements.refreshMcpClients.addEventListener("click", loadMcpClients);
elements.mcpClientList.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLButtonElement)) {
    return;
  }
  const action = target.dataset.action;
  const clientId = target.dataset.clientId;
  if ((action === "extend" || action === "disconnect") && clientId) {
    manageMcpClient(action, clientId);
  }
});

Promise.all([loadMcpStatus(), loadMcpClients()]);
