const {
  ItemView,
  MarkdownRenderer,
  MarkdownView,
  Notice,
  Plugin,
  PluginSettingTab,
  requestUrl,
  Setting,
} = require("obsidian");

const VIEW_TYPE_ALEXANDRIA_LIBRARIAN = "alexandria-librarian-view";

const DEFAULT_SETTINGS = {
  apiUrl: "http://127.0.0.1:8000",
  operatorApiKey: "",
  defaultProject: "alexandria-hermes",
  autoSaveTranscripts: false,
  preferredProviderId: "",
  preferredProfileId: "",
  useLangGraphWorkflow: true,
  showRelatedNotes: true,
  autoRefreshRelated: true,
};

module.exports = class AlexandriaLibrarianPlugin extends Plugin {
  async onload() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
    this.registerView(
      VIEW_TYPE_ALEXANDRIA_LIBRARIAN,
      (leaf) => new AlexandriaLibrarianView(leaf, this)
    );
    this.addCommand({
      id: "ask-alexandria-librarian",
      name: "Ask Alexandria Librarian",
      callback: () => this.activateView(),
    });
    this.addRibbonIcon("messages-square", "Ask Alexandria Librarian", () => {
      this.activateView();
    });
    this.addSettingTab(new AlexandriaLibrarianSettingTab(this.app, this));
  }

  async onunload() {
    this.app.workspace.detachLeavesOfType(VIEW_TYPE_ALEXANDRIA_LIBRARIAN);
  }

  async activateView() {
    this.app.workspace.detachLeavesOfType(VIEW_TYPE_ALEXANDRIA_LIBRARIAN);
    const leaf = this.app.workspace.getRightLeaf(false);
    await leaf.setViewState({
      type: VIEW_TYPE_ALEXANDRIA_LIBRARIAN,
      active: true,
    });
    this.app.workspace.revealLeaf(leaf);
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }
};

class AlexandriaLibrarianView extends ItemView {
  constructor(leaf, plugin) {
    super(leaf);
    this.plugin = plugin;
    this.lastResponse = null;
    this.lastWorkflow = null;
    this.history = [];
    this.currentQuery = "";
    this.answerContainer = null;
    this.delegateContainer = null;
    this.historyContainer = null;
    this.sourceContainer = null;
    this.statusEl = null;
    this.relatedContainer = null;
    this.graphActionContainer = null;
    this.workflowContainer = null;
  }

  getViewType() {
    return VIEW_TYPE_ALEXANDRIA_LIBRARIAN;
  }

  getDisplayText() {
    return "Alexandria Librarian";
  }

  getIcon() {
    return "messages-square";
  }

  async onOpen() {
    this.render();
  }

  async onClose() {}

  render() {
    const container = this.containerEl.children[1];
    container.empty();
    container.addClass("alexandria-librarian-view");

    container.createEl("h2", { text: "Alexandria Librarian" });
    container.createEl("p", {
      cls: "alexandria-muted",
      text: "Ask against the local Alexandria-Hermes Obsidian vault index.",
    });

    const activeInfo = container.createDiv({ cls: "alexandria-card" });
    activeInfo.createEl("strong", { text: "Active note" });
    activeInfo.createEl("div", {
      text: this.activePath() || "No active Markdown note",
    });

    this.relatedContainer = container.createDiv({ cls: "alexandria-related" });
    if (this.plugin.settings.showRelatedNotes) {
      this.refreshRelated();
    }

    this.historyContainer = container.createDiv({ cls: "alexandria-history" });
    this.renderHistory();

    const queryInput = container.createEl("textarea", {
      cls: "alexandria-query",
      attr: { rows: "6", placeholder: "Ask the librarian..." },
    });

    const controls = container.createDiv({ cls: "alexandria-controls" });
    const saveLabel = controls.createEl("label", { cls: "alexandria-checkbox" });
    const saveInput = saveLabel.createEl("input", { type: "checkbox" });
    saveInput.checked = this.plugin.settings.autoSaveTranscripts;
    saveLabel.createSpan({ text: "Save transcript" });

    const delegateLabel = controls.createEl("label", { cls: "alexandria-checkbox" });
    const delegateInput = delegateLabel.createEl("input", { type: "checkbox" });
    delegateLabel.createSpan({ text: "Ask OAuth librarian" });

    const workflowLabel = controls.createEl("label", { cls: "alexandria-checkbox" });
    const workflowInput = workflowLabel.createEl("input", { type: "checkbox" });
    workflowInput.checked = this.plugin.settings.useLangGraphWorkflow;
    workflowLabel.createSpan({ text: "Use LangGraph approval" });

    const providerInput = controls.createEl("input", {
      cls: "alexandria-inline-input",
      attr: { placeholder: "provider id or name" },
    });
    providerInput.value = this.plugin.settings.preferredProviderId || "";

    const profileInput = controls.createEl("input", {
      cls: "alexandria-inline-input",
      attr: { placeholder: "profile id or name" },
    });
    profileInput.value = this.plugin.settings.preferredProfileId || "";

    const refreshButton = controls.createEl("button", { text: "Refresh related" });
    refreshButton.addEventListener("click", async () => this.refreshRelated());

    const askButton = controls.createEl("button", {
      text: "Ask",
      cls: "mod-cta",
    });
    askButton.addEventListener("click", async () => {
      await this.ask(queryInput.value, {
        saveTranscript: saveInput.checked,
        delegateToLibrarian: delegateInput.checked,
        providerId: providerInput.value.trim(),
        profileId: profileInput.value.trim(),
        useWorkflow: workflowInput.checked,
      });
    });

    this.statusEl = container.createDiv({ cls: "alexandria-status" });
    this.answerContainer = container.createDiv({ cls: "alexandria-answer" });
    this.delegateContainer = container.createDiv({ cls: "alexandria-delegate" });
    this.sourceContainer = container.createDiv({ cls: "alexandria-sources" });
    this.workflowContainer = container.createDiv({ cls: "alexandria-workflow" });
    this.graphActionContainer = container.createDiv({ cls: "alexandria-graph-actions" });

    const actions = container.createDiv({ cls: "alexandria-actions" });
    this.actionButton(actions, "Append to current note", () => this.appendAnswer());
    this.actionButton(actions, "Link sources to current note", () => this.appendGraphLinks());
    this.actionButton(actions, "Create context note", () =>
      this.createNote("context")
    );
    this.actionButton(actions, "Create skill draft", () => this.createNote("skill"));
    this.actionButton(actions, "Create prompt template", () =>
      this.createNote("prompt")
    );
  }

  actionButton(parent, text, handler) {
    const button = parent.createEl("button", { text });
    button.addEventListener("click", async () => {
      try {
        await handler();
      } catch (error) {
        this.showError(error);
      }
    });
  }

  recordHistory(query, response, workflow) {
    const entryId =
      workflow?.thread_id ||
      response?.conversation_id ||
      `local-${Date.now().toString()}`;
    const entry = {
      id: entryId,
      query,
      response,
      workflow,
      status: workflow?.status || "answered",
      delegateStatus: response?.delegate_status || "local_only",
      transcriptPath: response?.transcript_path || null,
      timestamp: new Date().toLocaleTimeString(),
    };
    const existingIndex = this.history.findIndex((item) => item.id === entryId);
    if (existingIndex >= 0) {
      this.history.splice(existingIndex, 1);
    }
    this.history.unshift(entry);
    this.history = this.history.slice(0, 20);
    this.renderHistory();
  }

  renderHistory() {
    if (!this.historyContainer) {
      return;
    }
    this.historyContainer.empty();
    this.historyContainer.createEl("h3", { text: "Conversation history" });
    if (this.history.length === 0) {
      this.historyContainer.createEl("p", {
        cls: "alexandria-muted",
        text: "No local chat history yet. History stays in this pane only.",
      });
      return;
    }
    for (const entry of this.history) {
      const row = this.historyContainer.createDiv({ cls: "alexandria-history-row" });
      const button = row.createEl("button", {
        cls: "alexandria-history-button",
        text: this.truncate(entry.query, 72),
      });
      button.addEventListener("click", async () => {
        this.lastResponse = entry.response;
        this.lastWorkflow = entry.workflow;
        await this.renderAnswer(entry.response);
        await this.renderGraphActions(entry.response, entry.workflow);
        await this.renderDelegateResult(entry.response);
        this.renderWorkflowStatus(entry.workflow, entry.response);
        this.setStatus(`Restored ${entry.timestamp}`);
      });
      this.badge(row, entry.status);
      this.badge(row, `delegate:${entry.delegateStatus}`);
      if (entry.transcriptPath) {
        this.badge(row, "saved");
      }
      row.createSpan({ cls: "alexandria-muted", text: ` ${entry.timestamp}` });
    }
  }

  truncate(value, maxLength) {
    const text = String(value || "");
    return text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text;
  }

  badge(parent, text) {
    return parent.createSpan({
      cls: `alexandria-pill alexandria-pill-${this.badgeKind(text)}`,
      text: String(text || "unknown"),
    });
  }

  badgeKind(text) {
    const normalized = String(text || "").toLowerCase();
    if (normalized.includes("complete") || normalized.includes("saved")) {
      return "success";
    }
    if (normalized.includes("waiting") || normalized.includes("pending")) {
      return "warning";
    }
    if (normalized.includes("guidance") || normalized.includes("unavailable")) {
      return "muted";
    }
    return "default";
  }

  activeView() {
    return this.app.workspace.getActiveViewOfType(MarkdownView);
  }

  activePath() {
    return this.activeView()?.file?.path || null;
  }

  selectionText() {
    const view = this.activeView();
    if (!view) {
      return null;
    }
    const selection = view.editor.getSelection();
    return selection.trim() ? selection : null;
  }

  async ask(query, options) {
    if (!query.trim()) {
      new Notice("Ask Alexandria Librarian: enter a question first.");
      return;
    }
    this.currentQuery = query.trim();
    this.setStatus("Asking Alexandria...");
    if (options.useWorkflow) {
      await this.startWorkflow(query, options);
      return;
    }
    const response = await this.postJson("/obsidian/librarian/ask", {
      query,
      active_note_path: this.activePath(),
      selection: this.selectionText(),
      project: this.plugin.settings.defaultProject || null,
      save_transcript: options.saveTranscript,
      delegate_to_librarian: options.delegateToLibrarian,
      provider_id: options.providerId || null,
      profile_id: options.profileId || null,
    });
    this.lastResponse = response;
    this.lastWorkflow = null;
    this.recordHistory(this.currentQuery, response, null);
    await this.renderAnswer(response);
    await this.renderGraphActions(response, null);
    await this.renderDelegateResult(response);
    this.renderWorkflowStatus(null, response);
    this.setStatus(response.transcript_path ? `Saved: ${response.transcript_path}` : "Ready");
  }

  async startWorkflow(query, options) {
    const workflow = await this.postJson("/obsidian/librarian/workflows", {
      query,
      active_note_path: this.activePath(),
      selection: this.selectionText(),
      project: this.plugin.settings.defaultProject || null,
      save_transcript: false,
      delegate_to_librarian: options.delegateToLibrarian,
      provider_id: options.providerId || null,
      profile_id: options.profileId || null,
    });
    this.lastWorkflow = workflow;
    this.lastResponse = this.responseFromWorkflow(workflow);
    this.recordHistory(this.currentQuery, this.lastResponse, workflow);
    await this.renderAnswer(this.lastResponse);
    await this.renderGraphActions(this.lastResponse, workflow);
    await this.renderDelegateResult(this.lastResponse);
    this.renderWorkflowStatus(workflow, this.lastResponse);
    this.setStatus(`Workflow waiting: ${workflow.thread_id}`);
  }


  async refreshRelated() {
    if (!this.relatedContainer) {
      return;
    }
    this.relatedContainer.empty();
    this.relatedContainer.createEl("h3", { text: "Related notes" });
    const activePath = this.activePath();
    if (!activePath) {
      this.relatedContainer.createEl("p", {
        cls: "alexandria-muted",
        text: "Open a Markdown note to load related notes.",
      });
      return;
    }
    try {
      const response = await this.getJson(
        `/obsidian/notes/by-path/related?path=${encodeURIComponent(activePath)}`
      );
      const items = Array.isArray(response.items) ? response.items : [];
      if (items.length === 0) {
        this.relatedContainer.createEl("p", {
          cls: "alexandria-muted",
          text: "No graph edges found yet. Reindex after adding wikilinks.",
        });
        return;
      }
      const list = this.relatedContainer.createEl("ul");
      for (const item of items) {
        const note = item.note || {};
        const row = list.createEl("li");
        const link = row.createEl("a", { text: note.wikilink || note.path, href: "#" });
        link.addEventListener("click", async (event) => {
          event.preventDefault();
          await this.openSource(note.path);
        });
        row.createSpan({
          cls: "alexandria-badge",
          text: ` ${item.relation || "related"} · ${item.direction || "edge"}`,
        });
      }
    } catch (error) {
      this.relatedContainer.createEl("p", {
        cls: "alexandria-muted",
        text: `Related notes unavailable: ${error.message || error}`,
      });
    }
  }

  async renderAnswer(response) {
    this.answerContainer.empty();
    this.answerContainer.createEl("h3", { text: "Answer" });
    const markdownTarget = this.answerContainer.createDiv();
    await MarkdownRenderer.render(
      this.app,
      response.answer_markdown || "_No answer returned._",
      markdownTarget,
      this.activePath() || "",
      this
    );

    this.sourceContainer.empty();
    this.sourceContainer.createEl("h3", { text: "Sources" });
    const refs = Array.isArray(response.source_refs) ? response.source_refs : [];
    if (refs.length === 0) {
      this.sourceContainer.createEl("p", {
        cls: "alexandria-muted",
        text: "No source notes returned.",
      });
      return;
    }
    const list = this.sourceContainer.createEl("ul");
    for (const ref of refs) {
      const item = list.createEl("li");
      const link = item.createEl("a", {
        text: ref.wikilink || ref.title || ref.path,
        href: "#",
      });
      link.addEventListener("click", async (event) => {
        event.preventDefault();
        await this.openSource(ref.path);
      });
    }
  }


  async renderDelegateResult(response) {
    if (!this.delegateContainer) {
      return;
    }
    this.delegateContainer.empty();
    this.delegateContainer.createEl("h3", { text: "GPT OAuth Librarian" });
    const status = response.delegate_status || "local_only";
    this.badge(this.delegateContainer, status);
    if (response.provider_id || response.profile_id) {
      this.delegateContainer.createEl("p", {
        cls: "alexandria-muted",
        text: `Provider ${response.provider_id || "auto"} · profile ${
          response.profile_id || "auto"
        }`,
      });
    }
    const delegateMarkdown = this.delegateMarkdown(response.answer_markdown || "");
    if (!delegateMarkdown) {
      this.delegateContainer.createEl("p", {
        cls: "alexandria-muted",
        text:
          status === "local_only"
            ? "No GPT OAuth delegate result yet."
            : "Delegate status is available, but no delegate summary was returned.",
      });
      return;
    }
    const target = this.delegateContainer.createDiv({
      cls: "alexandria-delegate-body",
    });
    await MarkdownRenderer.render(
      this.app,
      delegateMarkdown,
      target,
      this.activePath() || "",
      this
    );
  }

  delegateMarkdown(answerMarkdown) {
    const match = String(answerMarkdown).match(
      /(?:^|\n)## GPT OAuth Librarian\s*\n([\s\S]*)/u
    );
    return match ? match[1].trim() : "";
  }

  renderWorkflowStatus(workflow, response) {
    if (!this.workflowContainer) {
      return;
    }
    this.workflowContainer.empty();
    this.workflowContainer.createEl("h3", { text: "Workflow status" });
    if (!workflow) {
      this.workflowContainer.createEl("p", {
        cls: "alexandria-muted",
        text: `Direct ask · ${response.conversation_id || "local"}`,
      });
      this.badge(this.workflowContainer, response.delegate_status || "local_only");
      return;
    }
    const header = this.workflowContainer.createDiv({
      cls: "alexandria-workflow-badges",
    });
    this.badge(header, workflow.status || "unknown");
    this.badge(header, response.delegate_status || "local_only");
    if (workflow.transcript_path || response.transcript_path) {
      this.badge(header, "saved");
    }
    this.workflowContainer.createEl("p", {
      cls: "alexandria-muted",
      text: `Thread ${workflow.thread_id}`,
    });
    const completed = Array.isArray(workflow.completed_actions)
      ? workflow.completed_actions
      : [];
    if (completed.length > 0) {
      const list = this.workflowContainer.createEl("ul");
      for (const action of completed) {
        list.createEl("li", { text: String(action) });
      }
    }
  }


  async renderGraphActions(response, workflow) {
    if (!this.graphActionContainer) {
      return;
    }
    this.graphActionContainer.empty();
    this.graphActionContainer.createEl("h3", { text: "Proposed graph actions" });
    const actions = Array.isArray(response.action_preview) ? response.action_preview : [];
    if (response.delegate_status) {
      this.graphActionContainer.createEl("p", {
        cls: "alexandria-muted",
        text: `Delegate: ${response.delegate_status}`,
      });
    }
    if (workflow?.status === "waiting_for_approval") {
      this.renderWorkflowApproval(workflow);
      return;
    }
    const list = this.graphActionContainer.createEl("ul");
    for (const action of actions) {
      list.createEl("li", { text: action });
    }
    if (this.workflowContainer) {
      this.workflowContainer.empty();
      this.workflowContainer.createEl("p", {
        cls: "alexandria-muted",
        text: `Conversation: ${response.conversation_id || "local"}`,
      });
    }
  }

  renderWorkflowApproval(workflow) {
    const actions = Array.isArray(workflow.pending_actions) ? workflow.pending_actions : [];
    if (actions.length === 0) {
      this.graphActionContainer.createEl("p", {
        cls: "alexandria-muted",
        text: "No pending workflow actions.",
      });
      return;
    }
    const form = this.graphActionContainer.createDiv({ cls: "alexandria-workflow-form" });
    const selected = new Set();
    for (const action of actions) {
      const actionId = String(action.id || "");
      if (!actionId) {
        continue;
      }
      const card = form.createDiv({ cls: "alexandria-action-card" });
      const label = card.createEl("label", { cls: "alexandria-checkbox" });
      const input = label.createEl("input", { type: "checkbox" });
      if (actionId === "save_transcript" && this.plugin.settings.autoSaveTranscripts) {
        input.checked = true;
        selected.add(actionId);
      }
      if (actionId === "ask_oauth_librarian") {
        input.checked = true;
        selected.add(actionId);
      }
      input.addEventListener("change", () => {
        if (input.checked) {
          selected.add(actionId);
        } else {
          selected.delete(actionId);
        }
      });
      label.createEl("strong", { text: action.label || actionId });
      this.badge(card, action.type || "action");
      card.createEl("p", {
        cls: "alexandria-muted",
        text: this.actionDescription(actionId),
      });
    }
    const resumeButton = form.createEl("button", {
      text: "Resume approved actions",
      cls: "mod-cta",
    });
    resumeButton.addEventListener("click", async () => {
      try {
        await this.resumeWorkflow(Array.from(selected));
      } catch (error) {
        this.showError(error);
      }
    });
  }

  actionDescription(actionId) {
    if (actionId === "save_transcript") {
      return "Save the current conversation as an Obsidian librarian_chat note.";
    }
    if (actionId === "create_context_note") {
      return "Create a context note from the local librarian answer.";
    }
    if (actionId === "add_graph_links") {
      return "Apply approved Alexandria graph/source links to the active note.";
    }
    if (actionId === "ask_oauth_librarian") {
      return "Ask the configured GPT OAuth librarian; tokens remain in the backend.";
    }
    return "Approve this backend workflow action.";
  }

  async resumeWorkflow(approvedActions) {
    if (!this.lastWorkflow?.thread_id) {
      new Notice("Start a LangGraph workflow first.");
      return;
    }
    this.setStatus("Resuming LangGraph workflow...");
    const workflow = await this.postJson(
      `/obsidian/librarian/workflows/${encodeURIComponent(this.lastWorkflow.thread_id)}/resume`,
      { approved_actions: approvedActions }
    );
    this.lastWorkflow = workflow;
    this.lastResponse = this.responseFromWorkflow(workflow);
    this.recordHistory(workflow.query || this.currentQuery, this.lastResponse, workflow);
    await this.renderAnswer(this.lastResponse);
    await this.renderGraphActions(this.lastResponse, workflow);
    await this.renderDelegateResult(this.lastResponse);
    this.renderWorkflowStatus(workflow, this.lastResponse);
    this.setStatus(`Workflow ${workflow.status}: ${workflow.thread_id}`);
  }

  responseFromWorkflow(workflow) {
    const response = workflow.response || {};
    const completed = Array.isArray(workflow.completed_actions) ? workflow.completed_actions : [];
    const delegated = completed.some((action) => String(action).startsWith("ask_oauth_librarian:"));
    const delegateStatus =
      response.delegate_status ||
      (delegated ? "completed" : workflow.status === "waiting_for_approval" ? "pending" : "local_only");
    return Object.assign({}, response, {
      conversation_id: response.conversation_id || workflow.thread_id,
      transcript_path: workflow.transcript_path || response.transcript_path || null,
      delegate_status: delegateStatus,
      provider_id: response.provider_id || workflow.provider_id || null,
      profile_id: response.profile_id || workflow.profile_id || null,
    });
  }

  async openSource(path) {
    if (!path || path.includes("..")) {
      new Notice("Alexandria source path is invalid.");
      return;
    }
    const linkText = path.replace(/\.md$/u, "");
    await this.app.workspace.openLinkText(linkText, "", false);
  }

  async appendAnswer() {
    if (!this.lastResponse?.answer_markdown) {
      new Notice("Ask the librarian before appending an answer.");
      return;
    }
    const view = this.activeView();
    if (!view?.file) {
      new Notice("Open a Markdown note before appending.");
      return;
    }
    await this.app.vault.append(
      view.file,
      `\n\n## Alexandria Librarian\n\n${this.lastResponse.answer_markdown}\n`
    );
    new Notice("Alexandria answer appended to current note.");
  }


  async appendGraphLinks() {
    const refs = Array.isArray(this.lastResponse?.source_refs) ? this.lastResponse.source_refs : [];
    if (refs.length === 0) {
      new Notice("Ask the librarian before linking sources.");
      return;
    }
    const view = this.activeView();
    if (!view?.file) {
      new Notice("Open a Markdown note before linking sources.");
      return;
    }
    const current = await this.app.vault.read(view.file);
    const block = this.alexandriaLinksBlock(refs);
    const next = current.match(/<!-- ALEXANDRIA-LINKS:START -->[\s\S]*<!-- ALEXANDRIA-LINKS:END -->/u)
      ? current.replace(/<!-- ALEXANDRIA-LINKS:START -->[\s\S]*<!-- ALEXANDRIA-LINKS:END -->/u, block)
      : `${current.trimEnd()}\n\n${block}\n`;
    await this.app.vault.modify(view.file, next);
    new Notice("Alexandria source wikilinks added to current note.");
    await this.refreshRelated();
  }

  alexandriaLinksBlock(refs) {
    const lines = refs.map((ref) => `- ${ref.wikilink || `[[${String(ref.path || "").replace(/\.md$/u, "")}]]`} — cites`);
    return [
      "<!-- ALEXANDRIA-LINKS:START -->",
      "## Alexandria Links",
      "",
      "### Sources",
      ...lines,
      "<!-- ALEXANDRIA-LINKS:END -->",
    ].join("\n");
  }

  async createNote(alexandriaType) {
    if (!this.lastResponse?.answer_markdown) {
      new Notice("Ask the librarian before creating a note.");
      return;
    }
    const titles = {
      context: "Context Note",
      skill: "Skill Draft",
      prompt: "Prompt Template",
    };
    const title = titles[alexandriaType] || "Context Note";
    const response = await this.postJson("/obsidian/notes", {
      title: `Alexandria ${title}`,
      body: this.lastResponse.answer_markdown,
      alexandria_type: alexandriaType,
      tags: ["alexandria", "librarian", alexandriaType],
      project: this.plugin.settings.defaultProject || null,
      source: "obsidian-plugin",
    });
    new Notice(`Created ${response.path || response.id}`);
    if (response.path) {
      await this.openSource(response.path);
    }
  }


  async getJson(path) {
    const url = `${this.plugin.settings.apiUrl.replace(/\/$/u, "")}${path}`;
    const headers = {};
    if (this.plugin.settings.operatorApiKey) {
      headers["X-Alexandria-Operator-Key"] = this.plugin.settings.operatorApiKey;
    }
    const response = await requestUrl({ url, method: "GET", headers });
    if (response.status < 200 || response.status >= 300) {
      throw new Error(`Alexandria request failed (${response.status})`);
    }
    return response.json;
  }

  async postJson(path, payload) {
    const url = `${this.plugin.settings.apiUrl.replace(/\/$/u, "")}${path}`;
    const headers = { "Content-Type": "application/json" };
    if (this.plugin.settings.operatorApiKey) {
      headers["X-Alexandria-Operator-Key"] = this.plugin.settings.operatorApiKey;
    }
    const response = await requestUrl({
      url,
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });
    if (response.status < 200 || response.status >= 300) {
      throw new Error(`Alexandria request failed (${response.status})`);
    }
    return response.json;
  }

  setStatus(text) {
    if (this.statusEl) {
      this.statusEl.setText(text);
    }
  }

  showError(error) {
    const message = error instanceof Error ? error.message : String(error);
    this.setStatus(message);
    new Notice(`Alexandria Librarian: ${message}`);
  }
}

class AlexandriaLibrarianSettingTab extends PluginSettingTab {
  constructor(app, plugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display() {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.createEl("h2", { text: "Alexandria Librarian" });

    new Setting(containerEl)
      .setName("Alexandria API URL")
      .setDesc("Local Alexandria-Hermes backend URL.")
      .addText((text) =>
        text
          .setPlaceholder(DEFAULT_SETTINGS.apiUrl)
          .setValue(this.plugin.settings.apiUrl)
          .onChange(async (value) => {
            this.plugin.settings.apiUrl = value.trim() || DEFAULT_SETTINGS.apiUrl;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Operator API key")
      .setDesc(
        "Optional local Obsidian setting. Leave blank for read-only librarian chat."
      )
      .addText((text) =>
        text
          .setPlaceholder("Optional operator key")
          .setValue(this.plugin.settings.operatorApiKey)
          .onChange(async (value) => {
            this.plugin.settings.operatorApiKey = value.trim();
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Default project")
      .setDesc("Project metadata sent with librarian asks and created notes.")
      .addText((text) =>
        text
          .setPlaceholder(DEFAULT_SETTINGS.defaultProject)
          .setValue(this.plugin.settings.defaultProject)
          .onChange(async (value) => {
            this.plugin.settings.defaultProject = value.trim();
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Preferred provider id")
      .setDesc("Optional backend provider id for delegated librarian asks. No OAuth token is stored here.")
      .addText((text) =>
        text
          .setPlaceholder("codex-oauth")
          .setValue(this.plugin.settings.preferredProviderId)
          .onChange(async (value) => {
            this.plugin.settings.preferredProviderId = value.trim();
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Preferred profile id")
      .setDesc("Optional backend librarian profile id for delegated asks.")
      .addText((text) =>
        text
          .setPlaceholder("research-critic")
          .setValue(this.plugin.settings.preferredProfileId)
          .onChange(async (value) => {
            this.plugin.settings.preferredProfileId = value.trim();
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Use LangGraph approval workflow")
      .setDesc("Ask through backend LangGraph workflow endpoints and approve actions before writes/delegation.")
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.useLangGraphWorkflow)
          .onChange(async (value) => {
            this.plugin.settings.useLangGraphWorkflow = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Show related notes")
      .setDesc("Show graph-related notes in the Alexandria side pane.")
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.showRelatedNotes)
          .onChange(async (value) => {
            this.plugin.settings.showRelatedNotes = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Auto-save transcripts")
      .setDesc("Default the chat pane to saving transcripts as Obsidian notes.")
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.autoSaveTranscripts)
          .onChange(async (value) => {
            this.plugin.settings.autoSaveTranscripts = value;
            await this.plugin.saveSettings();
          })
      );
  }
}
