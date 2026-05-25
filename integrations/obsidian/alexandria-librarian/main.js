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
    this.answerContainer = null;
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

    const providerInput = controls.createEl("input", {
      cls: "alexandria-inline-input",
      attr: { placeholder: "provider id" },
    });
    providerInput.value = this.plugin.settings.preferredProviderId || "";

    const profileInput = controls.createEl("input", {
      cls: "alexandria-inline-input",
      attr: { placeholder: "profile id" },
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
      });
    });

    this.statusEl = container.createDiv({ cls: "alexandria-status" });
    this.answerContainer = container.createDiv({ cls: "alexandria-answer" });
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
    this.setStatus("Asking Alexandria...");
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
    await this.renderAnswer(response);
    await this.renderGraphActions(response);
    this.setStatus(response.transcript_path ? `Saved: ${response.transcript_path}` : "Ready");
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


  async renderGraphActions(response) {
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
    const title = alexandriaType === "skill" ? "Skill Draft" : "Context Note";
    const response = await this.postJson("/obsidian/notes", {
      title: `Alexandria ${title}`,
      body: this.lastResponse.answer_markdown,
      alexandria_type: alexandriaType,
      tags: ["alexandria", "librarian"],
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
