import assert from "node:assert/strict";

import {
  createAgentPayload,
  isAgentRequestRecord,
  updateAgentPayload,
} from "../src/app/api/agents/agent-route-payload.ts";

assert.equal(isAgentRequestRecord({}), true);
assert.equal(isAgentRequestRecord([]), false);

const createResult = createAgentPayload({
  name: " Hermes Librarian ",
  provider: "OPENAI_CODEX",
  description: " ",
  capabilities: ["library-search"],
  preferredLibrarianProvider: null,
  preferredLibrarianModel: "gpt-5.5",
  maxLibrarianAgents: 2,
  librarianRolePrompt: "Use memory first.",
  librarianRole: "SPECIALIST",
  librarianSpecialties: ["library-search"],
  librarianRoutingPriority: 20,
  librarianEnabled: true,
});
assert.equal(createResult.ok, true);
assert.deepEqual(createResult.payload, {
  name: "Hermes Librarian",
  provider: "OPENAI_CODEX",
  description: null,
  capabilities: ["library-search"],
  preferredLibrarianProvider: null,
  preferredLibrarianModel: "gpt-5.5",
  maxLibrarianAgents: 2,
  librarianRolePrompt: "Use memory first.",
  librarianRole: "SPECIALIST",
  librarianSpecialties: ["library-search"],
  librarianRoutingPriority: 20,
  librarianEnabled: true,
});

for (const body of [
  {},
  { name: "Hermes", provider: "OPENAI_CODEX", capabilities: "search", maxLibrarianAgents: 1 },
  { name: "Hermes", provider: "OPENAI_CODEX", capabilities: ["search"], maxLibrarianAgents: 0 },
  { name: "Hermes", provider: "OPENAI_CODEX", capabilities: ["search", 1], maxLibrarianAgents: 1 },
  { name: "Hermes", provider: "OPENAI_CODEX", capabilities: ["search"], maxLibrarianAgents: 1, extra: true },
  {
    name: "Hermes",
    provider: "OPENAI_CODEX",
    capabilities: ["search"],
    maxLibrarianAgents: 1,
    librarianRole: "UNKNOWN",
    librarianSpecialties: ["search"],
    librarianRoutingPriority: 0,
    librarianEnabled: true,
  },
]) {
  assert.equal(createAgentPayload(body).ok, false);
}

const updateResult = updateAgentPayload({
  description: null,
  capabilities: ["context-recall"],
  maxLibrarianAgents: 6,
  librarianRole: "QUALITY_REVIEWER",
  librarianSpecialties: ["context-recall"],
  librarianRoutingPriority: 5,
  librarianEnabled: false,
});
assert.equal(updateResult.ok, true);
assert.deepEqual(updateResult.payload, {
  description: null,
  capabilities: ["context-recall"],
  maxLibrarianAgents: 6,
  librarianRole: "QUALITY_REVIEWER",
  librarianSpecialties: ["context-recall"],
  librarianRoutingPriority: 5,
  librarianEnabled: false,
});

for (const body of [
  {},
  { name: null },
  { capabilities: "context-recall" },
  { capabilities: ["context-recall", 1] },
  { maxLibrarianAgents: null },
  { maxLibrarianAgents: 7 },
  { preferredLibrarianModel: 5 },
  { librarianRole: "UNKNOWN" },
  { librarianSpecialties: ["context-recall", 1] },
  { librarianRoutingPriority: -1 },
  { librarianEnabled: "yes" },
  { description: null, extra: true },
]) {
  assert.equal(updateAgentPayload(body).ok, false);
}

console.log("agent route payload contract ok");
