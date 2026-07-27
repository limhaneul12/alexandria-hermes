"use strict";

const state = {
  providerId: null,
  verificationUrl: null,
};

const elements = {
  coreDot: document.querySelector("#core-dot"),
  coreStatus: document.querySelector("#core-status"),
  semanticDot: document.querySelector("#semantic-dot"),
  semanticStatus: document.querySelector("#semantic-status"),
  librarianDot: document.querySelector("#librarian-dot"),
  librarianStatus: document.querySelector("#librarian-status"),
  oauthPill: document.querySelector("#oauth-pill"),
  oauthDetail: document.querySelector("#oauth-detail"),
  oauthStart: document.querySelector("#oauth-start"),
  oauthPoll: document.querySelector("#oauth-poll"),
  oauthRefresh: document.querySelector("#oauth-refresh"),
  oauthMessage: document.querySelector("#oauth-message"),
  devicePanel: document.querySelector("#device-panel"),
  deviceCode: document.querySelector("#device-code"),
  deviceExpiry: document.querySelector("#device-expiry"),
  verificationLink: document.querySelector("#verification-link"),
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
};

function setDot(dot, tone) {
  dot.className = `status-dot ${tone}`;
}

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
      // Preserve the HTTP status when the response is not JSON.
    }
    throw new Error(detail);
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

async function loadReadiness() {
  try {
    const readiness = await api("/operations/readiness");
    const coreHealthy = readiness.database.reachable
      && readiness.vault.exists
      && readiness.vault.readable
      && readiness.rag.fts === "HEALTHY";
    elements.coreStatus.textContent = coreHealthy ? "사용 가능" : "점검 필요";
    setDot(elements.coreDot, coreHealthy ? "ok" : "error");

    const semanticHealthy = readiness.rag.effective_strategy === "HYBRID"
      && readiness.rag.embedding === "HEALTHY"
      && readiness.rag.vector === "HEALTHY";
    elements.semanticStatus.textContent = semanticHealthy
      ? "Hybrid 준비"
      : `${readiness.rag.effective_strategy} · 복구 필요`;
    setDot(elements.semanticDot, semanticHealthy ? "ok" : "warn");
  } catch (error) {
    elements.coreStatus.textContent = "상태 조회 실패";
    elements.semanticStatus.textContent = "상태 조회 실패";
    setDot(elements.coreDot, "error");
    setDot(elements.semanticDot, "error");
  }
}

async function findCodexProvider() {
  if (state.providerId) {
    return state.providerId;
  }
  const providers = await api("/settings/connections");
  const provider = providers.find(
    (item) => item.provider_type === "OPENAI_CODEX" && item.auth_type === "OAUTH",
  );
  if (provider) {
    state.providerId = provider.id;
    return provider.id;
  }
  return null;
}

async function ensureCodexProvider() {
  const existingProviderId = await findCodexProvider();
  if (existingProviderId) {
    return existingProviderId;
  }
  const created = await api("/settings/connections", {
    method: "POST",
    body: JSON.stringify({
      name: "codex-oauth-local",
      provider_type: "OPENAI_CODEX",
      auth_type: "OAUTH",
      enabled: true,
      config: { model: "gpt-5.5" },
    }),
  });
  state.providerId = created.id;
  return created.id;
}

function renderOAuthStatus(status) {
  const connected = status.connected === true;
  elements.oauthPill.textContent = status.status;
  elements.oauthPill.className = connected && !status.refresh_required
    ? "pill ok"
    : "pill warn";
  const expiry = status.expires_at ? ` · 만료 ${status.expires_at}` : "";
  if (status.next_action === "refresh") {
    elements.oauthDetail.textContent = `토큰 갱신 필요${expiry}`;
  } else if (status.next_action === "poll") {
    elements.oauthDetail.textContent = "OpenAI 승인을 기다리는 중입니다.";
  } else if (status.reconnect_required) {
    elements.oauthDetail.textContent = `${status.message || "재연결이 필요합니다."} · 연결 시작을 눌러주세요.`;
  } else {
    elements.oauthDetail.textContent = `연결됨${expiry}`;
  }
  elements.oauthRefresh.hidden = status.next_action !== "refresh";
  elements.oauthStart.textContent = status.reconnect_required ? "OpenAI 재연결" : "OpenAI 연결 시작";
  elements.librarianStatus.textContent = connected ? "연결됨" : "선택 기능";
  setDot(elements.librarianDot, connected ? "ok" : "warn");
}

async function loadOAuthStatus() {
  try {
    const providerId = await findCodexProvider();
    if (!providerId) {
      elements.oauthPill.textContent = "not connected";
      elements.oauthPill.className = "pill warn";
      elements.oauthDetail.textContent = "연결 시작 버튼으로 OpenAI OAuth를 설정하세요.";
      elements.librarianStatus.textContent = "연결 필요";
      setDot(elements.librarianDot, "warn");
      return;
    }
    const status = await api(`/settings/connections/${encodeURIComponent(providerId)}/oauth/status`);
    renderOAuthStatus(status);
  } catch (error) {
    elements.oauthPill.textContent = "not connected";
    elements.oauthPill.className = "pill warn";
    elements.oauthDetail.textContent = "연결 시작 버튼으로 OpenAI OAuth를 설정하세요.";
    elements.librarianStatus.textContent = "연결 필요";
    setDot(elements.librarianDot, "warn");
    setMessage(elements.oauthMessage, error.message, true);
  }
}

function safeVerificationUrl(candidate) {
  const url = new URL(candidate);
  if (url.protocol !== "https:" || url.hostname !== "auth.openai.com") {
    throw new Error("허용되지 않은 OpenAI 인증 주소입니다.");
  }
  return url.toString();
}

async function startOAuth() {
  elements.oauthStart.disabled = true;
  setMessage(elements.oauthMessage, "OpenAI 기기 인증을 시작합니다…");
  try {
    const providerId = await ensureCodexProvider();
    const result = await api(
      `/settings/connections/${encodeURIComponent(providerId)}/oauth/start`,
      { method: "POST" },
    );
    state.verificationUrl = safeVerificationUrl(
      result.verification_uri_complete || result.verification_uri,
    );
    elements.deviceCode.textContent = result.user_code;
    elements.verificationLink.href = state.verificationUrl;
    elements.deviceExpiry.textContent = `만료: ${result.expires_at}`;
    elements.devicePanel.hidden = false;
    elements.oauthPoll.disabled = false;
    elements.oauthPill.textContent = result.status;
    elements.oauthPill.className = "pill warn";
    elements.oauthDetail.textContent = "OpenAI 인증 페이지에서 코드를 승인하세요.";
    setMessage(elements.oauthMessage, "새 탭에서 인증한 뒤 연결 확인을 누르세요.");
    window.open(state.verificationUrl, "_blank", "noopener,noreferrer");
  } catch (error) {
    setMessage(elements.oauthMessage, error.message, true);
  } finally {
    elements.oauthStart.disabled = false;
  }
}

async function pollOAuth() {
  if (!state.providerId) {
    return;
  }
  elements.oauthPoll.disabled = true;
  setMessage(elements.oauthMessage, "OpenAI 승인 상태를 확인합니다…");
  try {
    const status = await api(
      `/settings/connections/${encodeURIComponent(state.providerId)}/oauth/poll`,
      { method: "POST" },
    );
    renderOAuthStatus(status);
    if (status.connected) {
      elements.devicePanel.hidden = true;
      setMessage(elements.oauthMessage, "OpenAI Librarian 연결이 완료되었습니다.");
      return;
    }
    elements.oauthPoll.disabled = false;
    setMessage(elements.oauthMessage, status.message || "아직 승인을 기다리고 있습니다.");
  } catch (error) {
    elements.oauthPoll.disabled = false;
    setMessage(elements.oauthMessage, error.message, true);
  }
}

async function refreshOAuth() {
  try {
    const providerId = await ensureCodexProvider();
    const status = await api(
      `/settings/connections/${encodeURIComponent(providerId)}/oauth/refresh`,
      { method: "POST" },
    );
    renderOAuthStatus(status);
    setMessage(elements.oauthMessage, status.message || "토큰 상태를 갱신했습니다.");
  } catch (error) {
    setMessage(elements.oauthMessage, error.message, true);
  }
}

async function loadMcpStatus() {
  try {
    const status = await api("/connect/status");
    elements.mcpEndpoint.textContent = status.mcp_endpoint;
    elements.mcpMode.textContent = status.mcp_auth_mode;
    elements.mcpIssuer.textContent = status.mcp_oauth_issuer || "—";
    if (status.mcp_oauth_enabled) {
      elements.mcpNotice.textContent = "MCP OAuth가 활성화되어 있습니다. 클라이언트에 Endpoint를 등록하면 브라우저 승인 화면이 열립니다.";
      elements.mcpNotice.className = "notice ok";
      elements.generatePairingCode.hidden = false;
    } else {
      elements.mcpNotice.textContent = "현재 MCP 인증이 비활성화되어 있습니다. P1 페어링 코드 적용 후 local_oauth2 모드에서 안전하게 연결할 수 있습니다.";
      elements.mcpNotice.className = "notice warn";
    }
    if (!status.local_only) {
      elements.mcpNotice.textContent += " 이 페이지는 로컬호스트 밖에서 열렸습니다. 공개 배포에는 HTTPS와 운영자 인증이 필요합니다.";
      elements.mcpNotice.className = "notice warn";
    }
  } catch (error) {
    elements.mcpNotice.textContent = "MCP 상태를 불러오지 못했습니다.";
    elements.mcpNotice.className = "notice warn";
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
        ? "일회용 코드를 생성하고 클립보드에 복사했습니다. MCP 승인 페이지에 입력하세요."
        : "일회용 코드를 생성했습니다. MCP 승인 페이지에 직접 입력하세요.",
    );
  } catch (error) {
    setMessage(elements.mcpMessage, error.message, true);
  } finally {
    elements.generatePairingCode.disabled = false;
  }
}

elements.oauthStart.addEventListener("click", startOAuth);
elements.oauthPoll.addEventListener("click", pollOAuth);
elements.oauthRefresh.addEventListener("click", refreshOAuth);
elements.copyMcpEndpoint.addEventListener("click", copyMcpEndpoint);
elements.generatePairingCode.addEventListener("click", generatePairingCode);

Promise.all([loadReadiness(), loadOAuthStatus(), loadMcpStatus()]);
