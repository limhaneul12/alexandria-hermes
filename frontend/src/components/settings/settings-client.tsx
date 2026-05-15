"use client";

import { type FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Cloud,
  Gauge,
  KeyRound,
  Languages,
  PanelLeftClose,
  Plug,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Trash2,
  type LucideIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  createAgent,
  createLibrarianProvider,
  deleteAgent,
  deleteLibrarianProvider,
  fetchExternalArchiveCandidates,
  fetchAgents,
  fetchLibrarianOAuthStatus,
  fetchLibrarianProviders,
  fetchRagStatus,
  importExternalArchiveCandidates,
  pollLibrarianOAuth,
  refreshLibrarianOAuth,
  startLibrarianOAuth,
  testLibrarianProvider,
  updateAgent,
  updateLibrarianProvider,
} from "@/lib/api";
import { languageOptions, t, type Language } from "@/lib/i18n";
import { useLibraryStore } from "@/store/library-store";
import {
  type AuthType,
  type AgentDTO,
  type AgentCreateDTO,
  type AgentUpdateDTO,
  type LibrarianOAuthStatusDTO,
  type LibrarianProfileRole,
  type LibrarianProviderCreateDTO,
  type LibrarianProviderCredentialMode,
  type LibrarianProviderDTO,
  type ProviderType,
} from "@/types/library";

const selectClassName =
  "h-11 rounded-md border border-[#cfc8b8] bg-white/80 px-3 py-2 text-sm font-medium text-[#111111] outline-none transition hover:border-[#a39b8d] focus-visible:border-[#111111] focus-visible:ring-2 focus-visible:ring-[#111111]/10";

const fieldClassName = "space-y-2 text-sm font-semibold text-[#28241f]";
const helperClassName = "text-xs font-normal leading-5 text-[#6f6a60]";

type SettingsSection = "library" | "librarians";
const oauthAutoPollMaxAttempts = 180;
const oauthAutoPollMinimumDelayMs = 3000;
const librarianModelOptions = ["gpt-5.5", "gpt-5.4", "gpt-5.4-mini"] as const;
const librarianProfileRoles = [
  "DEFAULT_SEARCH",
  "SPECIALIST",
  "QUALITY_REVIEWER",
  "ARCHIVIST_CURATOR",
] as const satisfies readonly LibrarianProfileRole[];
const defaultAgentSpecialties = "library-search, context-recall, skill-acquisition";

type OAuthDeviceInstruction = {
  providerId: string;
  userCode: string;
  authorizationUrl: string;
  intervalSeconds: number;
};

function formatMessage(template: string, values: Record<string, string>) {
  return Object.entries(values).reduce(
    (message, [key, value]) => message.replace(`{${key}}`, value),
    template,
  );
}

function credentialLabel(language: Language, authType: AuthType, providerType?: ProviderType) {
  if (providerType === "MINIO") return t(language, "minioCredential");
  if (authType === "OAUTH") return t(language, "oauthAuthorization");
  if (authType === "NONE") return t(language, "credentialNone");
  return t(language, "apiKey");
}

function configSummary(language: Language, config: Record<string, unknown>) {
  const entries = Object.entries(config).filter(([, value]) => value !== "" && value !== undefined);
  if (entries.length === 0) return t(language, "noExtraConfig");
  return entries.map(([key, value]) => `${key}: ${String(value)}`).join(" · ");
}

function getProviderStatus(language: Language, enabled: boolean) {
  const status = enabled ? t(language, "providerAssignable") : t(language, "providerDisabled");
  return `${t(language, "providerStatus")}: ${status}`;
}

function prepareOAuthPopup() {
  const popup = window.open("about:blank", "_blank");
  if (popup) {
    popup.opener = null;
  }
  return popup;
}

function openOAuthAuthorization(url: string, popup: Window | null) {
  if (popup) {
    popup.location.href = url;
    return;
  }
  window.open(url, "_blank", "noopener,noreferrer");
}

function wait(ms: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function boundedAgentCount(value: string) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 1;
  return Math.min(Math.max(Math.trunc(parsed), 1), 6);
}

function specialtiesFromText(value: string): string[] {
  const specialties = value
    .split(",")
    .map((specialty) => specialty.trim())
    .filter(Boolean);
  return specialties.length > 0 ? specialties : defaultAgentSpecialties.split(", ");
}

function isOAuthTerminalStatus(result: LibrarianOAuthStatusDTO) {
  return (
    result.authorized ||
    result.status === "expired" ||
    result.status === "failed" ||
    result.status === "missing_refresh_token" ||
    result.status === "refresh_required"
  );
}

function ProviderOption({
  active,
  icon: Icon,
  title,
  description,
  onClick,
}: {
  active: boolean;
  icon: LucideIcon;
  title: string;
  description: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-xl border p-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black/15 ${active ? "border-[#111111] bg-[#f6f3ec]" : "border-[#d8d3c7] bg-white/65 hover:bg-white"}`}
    >
      <span className="flex items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[#d8d3c7] bg-white text-[#111111]"><Icon className="h-5 w-5" aria-hidden /></span>
        <span>
          <span className="block font-bold text-[#111111]">{title}</span>
          <span className="mt-1 block text-xs leading-5 text-[#625c52]">{description}</span>
        </span>
      </span>
    </button>
  );
}

function upsertProvider(
  providers: LibrarianProviderDTO[] | undefined,
  provider: LibrarianProviderDTO,
): LibrarianProviderDTO[] {
  if (!providers) return [provider];
  const exists = providers.some((currentProvider) => currentProvider.id === provider.id);
  if (!exists) return [provider, ...providers];
  return providers.map((currentProvider) =>
    currentProvider.id === provider.id ? provider : currentProvider,
  );
}

function removeProvider(
  providers: LibrarianProviderDTO[] | undefined,
  providerId: string,
): LibrarianProviderDTO[] {
  if (!providers) return [];
  return providers.filter((provider) => provider.id !== providerId);
}

export function SettingsClient({ section }: { section: SettingsSection }) {
  const queryClient = useQueryClient();
  const collapsed = useLibraryStore((state) => state.sidebarCollapsed);
  const setCollapsed = useLibraryStore((state) => state.setSidebarCollapsed);
  const language = useLibraryStore((state) => state.language);
  const setLanguage = useLibraryStore((state) => state.setLanguage);
  const viewMode = useLibraryStore((state) => state.viewMode);
  const setViewMode = useLibraryStore((state) => state.setViewMode);
  const clearFilters = useLibraryStore((state) => state.clearFilters);

  const [providerName, setProviderName] = useState("");
  const [providerType, setProviderType] = useState<ProviderType>("OPENAI");
  const [credential, setCredential] = useState("");
  const [model, setModel] = useState("gpt-5.5");
  const [baseUrl, setBaseUrl] = useState("");
  const [minioEndpoint, setMinioEndpoint] = useState("");
  const [minioBucket, setMinioBucket] = useState("");
  const [minioPrefix, setMinioPrefix] = useState("");
  const [minioRegion, setMinioRegion] = useState("");
  const [minioUseSsl, setMinioUseSsl] = useState(false);
  const [enabled, setEnabled] = useState(true);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [oauthDeviceInstruction, setOauthDeviceInstruction] =
    useState<OAuthDeviceInstruction | null>(null);
  const [agentProviderId, setAgentProviderId] = useState("");
  const [agentName, setAgentName] = useState("Hermes Librarian");
  const [agentModel, setAgentModel] = useState("gpt-5.5");
  const [agentRole, setAgentRole] = useState<LibrarianProfileRole>("SPECIALIST");
  const [agentMaxCount, setAgentMaxCount] = useState(1);
  const [agentSpecialties, setAgentSpecialties] = useState(defaultAgentSpecialties);
  const [agentRolePrompt, setAgentRolePrompt] = useState(
    "Use Alexandria-Hermes context, skills, and prompts before asking for external research.",
  );
  const [editingAgentId, setEditingAgentId] = useState<string | null>(null);
  const [isSavingProvider, setIsSavingProvider] = useState(false);
  const [pendingProviderDelete, setPendingProviderDelete] =
    useState<LibrarianProviderDTO | null>(null);
  const [pendingAgentDelete, setPendingAgentDelete] = useState<AgentDTO | null>(null);
  const authType: LibrarianProviderCredentialMode = providerType === "OPENAI_CODEX" ? "OAUTH" : "API_KEY";
  const isOAuthProvider = providerType === "OPENAI_CODEX";

  const providersQuery = useQuery({
    queryKey: ["librarian-providers"],
    queryFn: fetchLibrarianProviders,
  });
  const agentsQuery = useQuery({
    queryKey: ["agents"],
    queryFn: fetchAgents,
  });
  const ragStatusQuery = useQuery({
    queryKey: ["rag-status"],
    queryFn: fetchRagStatus,
  });
  const importCandidatesQuery = useQuery({
    queryKey: ["external-archive-candidates"],
    queryFn: () => fetchExternalArchiveCandidates(24),
    enabled: false,
    staleTime: 30_000,
  });
  const hasEnabledMinioProvider = useMemo(
    () => providersQuery.data?.some((provider) => provider.providerType === "MINIO" && provider.enabled) ?? false,
    [providersQuery.data],
  );
  const oauthProviders = useMemo(
    () =>
      providersQuery.data?.filter(
        (provider) => provider.providerType === "OPENAI_CODEX",
      ) ?? [],
    [providersQuery.data],
  );
  const oauthStatusQuery = useQuery({
    queryKey: ["librarian-oauth-statuses", oauthProviders.map((provider) => provider.id)],
    queryFn: async () => {
      const entries = await Promise.all(
        oauthProviders.map(async (provider) => {
          try {
            return [provider.id, await fetchLibrarianOAuthStatus(provider.id)] as const;
          } catch {
            return [provider.id, null] as const;
          }
        }),
      );
      return Object.fromEntries(entries) as Record<string, LibrarianOAuthStatusDTO | null>;
    },
    enabled: oauthProviders.length > 0,
  });
  const authorizedOAuthProviderIds = useMemo(
    () =>
      new Set(
        oauthProviders
          .filter((provider) => oauthStatusQuery.data?.[provider.id]?.authorized === true)
          .map((provider) => provider.id),
      ),
    [oauthProviders, oauthStatusQuery.data],
  );
  const assignableOAuthProviderIds = useMemo(
    () =>
      new Set(
        oauthProviders
          .filter((provider) => provider.enabled && authorizedOAuthProviderIds.has(provider.id))
          .map((provider) => provider.id),
      ),
    [authorizedOAuthProviderIds, oauthProviders],
  );
  const defaultAgentProviderId =
    oauthProviders.find((provider) => assignableOAuthProviderIds.has(provider.id))?.id ??
    oauthProviders[0]?.id ??
    "";
  const selectedAgentProviderId = agentProviderId || defaultAgentProviderId;
  const selectedAgentProviderAssignable =
    selectedAgentProviderId !== "" && assignableOAuthProviderIds.has(selectedAgentProviderId);
  const librarianAgents = useMemo(
    () =>
      agentsQuery.data?.filter(
        (agent) =>
          agent.provider === "OPENAI_CODEX" ||
          agent.preferredLibrarianProvider !== null,
      ) ?? [],
    [agentsQuery.data],
  );

  const providerConfig = useMemo(() => {
    const config: Record<string, unknown> = {};
    if (providerType === "MINIO") {
      if (minioEndpoint.trim()) config.endpoint = minioEndpoint.trim();
      if (minioBucket.trim()) config.bucket = minioBucket.trim();
      if (minioPrefix.trim()) config.prefix = minioPrefix.trim();
      if (minioRegion.trim()) config.region = minioRegion.trim();
      config.use_ssl = minioUseSsl;
    } else if (providerType === "OPENAI_CODEX") {
      return config;
    } else {
      if (model.trim()) config.model = model.trim();
      if (baseUrl.trim()) config.base_url = baseUrl.trim();
    }
    return config;
  }, [
    baseUrl,
    minioBucket,
    minioEndpoint,
    minioPrefix,
    minioRegion,
    minioUseSsl,
    model,
    providerType,
  ]);

  const updateProviderMutation = useMutation({
    mutationFn: ({ providerId, nextEnabled }: { providerId: string; nextEnabled: boolean }) =>
      updateLibrarianProvider(providerId, { enabled: nextEnabled }),
    onSuccess: (provider) => {
      setStatusMessage(formatMessage(t(language, "providerUpdated"), { name: provider.name }));
      queryClient.setQueryData<LibrarianProviderDTO[]>(["librarian-providers"], (providers) =>
        upsertProvider(providers, provider),
      );
      void queryClient.invalidateQueries({ queryKey: ["librarian-providers"] });
    },
    onError: () => setStatusMessage(t(language, "providerUpdateFailed")),
  });

  const deleteProviderMutation = useMutation({
    mutationFn: ({ providerId }: { providerId: string }) =>
      deleteLibrarianProvider(providerId),
    onSuccess: (_result, { providerId }) => {
      setStatusMessage(t(language, "providerDeleted"));
      setPendingProviderDelete(null);
      queryClient.setQueryData<LibrarianProviderDTO[]>(["librarian-providers"], (providers) =>
        removeProvider(providers, providerId),
      );
      void queryClient.invalidateQueries({ queryKey: ["librarian-providers"] });
      void queryClient.invalidateQueries({ queryKey: ["external-archive-candidates"] });
    },
    onError: () => setStatusMessage(t(language, "providerDeleteFailed")),
  });

  const testProviderMutation = useMutation({
    mutationFn: ({ providerId }: { providerId: string }) => testLibrarianProvider(providerId, "ping"),
    onSuccess: (result) => {
      setStatusMessage(
        result.ok
          ? t(language, "providerTestSucceeded")
          : formatMessage(t(language, "providerTestFailed"), { message: result.message }),
      );
    },
    onError: () => setStatusMessage(t(language, "providerTestRequestFailed")),
  });

  const createAgentMutation = useMutation({
    mutationFn: (payload: AgentCreateDTO) => createAgent(payload),
    onSuccess: (agent) => {
      setStatusMessage(
        formatMessage(t(language, "librarianAgentSaved"), { name: agent.name }),
      );
      resetAgentForm();
      void queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
    onError: () => setStatusMessage(t(language, "librarianAgentSaveFailed")),
  });

  const updateAgentMutation = useMutation({
    mutationFn: ({ agentId, payload }: { agentId: string; payload: AgentUpdateDTO }) =>
      updateAgent(agentId, payload),
    onSuccess: (agent) => {
      setStatusMessage(
        formatMessage(t(language, "librarianAgentUpdated"), { name: agent.name }),
      );
      resetAgentForm();
      void queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
    onError: () => setStatusMessage(t(language, "librarianAgentUpdateFailed")),
  });

  const deleteAgentMutation = useMutation({
    mutationFn: ({ agentId }: { agentId: string }) => deleteAgent(agentId),
    onSuccess: () => {
      setStatusMessage(t(language, "librarianAgentDeleted"));
      setPendingAgentDelete(null);
      resetAgentForm();
      void queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
    onError: () => setStatusMessage(t(language, "librarianAgentDeleteFailed")),
  });

  const oauthActionMutation = useMutation({
    mutationFn: async ({
      providerId,
      action,
    }: {
      providerId: string;
      action: "start" | "poll" | "status" | "refresh";
      popup: Window | null;
    }) => {
      if (action === "start") return startLibrarianOAuth(providerId);
      if (action === "poll") return pollLibrarianOAuth(providerId);
      if (action === "refresh") return refreshLibrarianOAuth(providerId);
      return fetchLibrarianOAuthStatus(providerId);
    },
    onSuccess: (result, variables) => {
      if ("verificationUri" in result) {
        const authorizationUrl = result.verificationUriComplete ?? result.verificationUri;
        openOAuthAuthorization(authorizationUrl, variables.popup);
        setOauthDeviceInstruction({
          providerId: result.providerId,
          userCode: result.userCode,
          authorizationUrl,
          intervalSeconds: result.intervalSeconds,
        });
        setStatusMessage(
          formatMessage(t(language, "oauthStartReady"), {
            url: authorizationUrl,
            code: result.userCode,
            seconds: String(result.intervalSeconds),
          }),
        );
        startOAuthAutoPoll(result.providerId, result.intervalSeconds);
        void queryClient.invalidateQueries({ queryKey: ["librarian-oauth-statuses"] });
        return;
      }
      updateOAuthStatusMessage(result);
      void queryClient.invalidateQueries({ queryKey: ["librarian-oauth-statuses"] });
    },
    onError: (_error, variables) => {
      if (variables.popup) {
        variables.popup.close();
      }
      setStatusMessage(t(language, "oauthActionFailed"));
    },
  });

  const importArchiveMutation = useMutation({
    mutationFn: () => importExternalArchiveCandidates(48),
    onSuccess: (result) => {
      setStatusMessage(
        formatMessage(t(language, "minioImportSucceeded"), {
          imported: String(result.importedCount),
          skipped: String(result.skippedCount),
        }),
      );
      void importCandidatesQuery.refetch();
      void queryClient.invalidateQueries({ queryKey: ["library"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: () => setStatusMessage(t(language, "minioImportFailed")),
  });

  async function handleCreateProvider(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedName = providerName.trim() || (isOAuthProvider ? t(language, "codexDefaultProviderName") : "");
    const trimmedCredential = credential.trim();
    if (!trimmedName || (!isOAuthProvider && !trimmedCredential)) {
      setStatusMessage(t(language, isOAuthProvider ? "nameRequired" : "nameAndCredentialRequired"));
      return;
    }
    if (providerType === "MINIO" && (!minioEndpoint.trim() || !minioBucket.trim())) {
      setStatusMessage(t(language, "minioRequiredFields"));
      return;
    }
    const payload: LibrarianProviderCreateDTO = {
      name: trimmedName,
      providerType,
      authType,
      enabled,
      config: providerConfig,
    };
    if (!isOAuthProvider) {
      payload.credential = trimmedCredential;
    }
    const oauthPopup = isOAuthProvider ? prepareOAuthPopup() : null;
    setCredential("");
    setIsSavingProvider(true);
    try {
      const provider = await createLibrarianProvider(payload);
      setStatusMessage(formatMessage(t(language, "providerSaved"), { name: provider.name }));
      queryClient.setQueryData<LibrarianProviderDTO[]>(["librarian-providers"], (providers) =>
        upsertProvider(providers, provider),
      );
      void queryClient.invalidateQueries({ queryKey: ["librarian-providers"] });
      if (provider.providerType === "OPENAI_CODEX") {
        const oauthStart = await startLibrarianOAuth(provider.id);
        const authorizationUrl = oauthStart.verificationUriComplete ?? oauthStart.verificationUri;
        openOAuthAuthorization(authorizationUrl, oauthPopup);
        setOauthDeviceInstruction({
          providerId: provider.id,
          userCode: oauthStart.userCode,
          authorizationUrl,
          intervalSeconds: oauthStart.intervalSeconds,
        });
        setStatusMessage(
          formatMessage(t(language, "oauthProviderSaved"), {
            name: provider.name,
            url: authorizationUrl,
            code: oauthStart.userCode,
          }),
        );
        startOAuthAutoPoll(provider.id, oauthStart.intervalSeconds);
        void queryClient.invalidateQueries({ queryKey: ["librarian-oauth-statuses"] });
      }
    } catch {
      if (oauthPopup) {
        oauthPopup.close();
      }
      setStatusMessage(t(language, "providerSaveFailed"));
    } finally {
      setIsSavingProvider(false);
    }
  }

  function requestDeleteProvider(provider: LibrarianProviderDTO) {
    setPendingProviderDelete(provider);
  }

  function confirmDeleteProvider() {
    if (!pendingProviderDelete) return;
    deleteProviderMutation.mutate({ providerId: pendingProviderDelete.id });
  }

  function resetAgentForm() {
    setEditingAgentId(null);
    setPendingAgentDelete(null);
    setAgentProviderId("");
    setAgentName("Hermes Librarian");
    setAgentModel("gpt-5.5");
    setAgentRole("SPECIALIST");
    setAgentMaxCount(1);
    setAgentSpecialties(defaultAgentSpecialties);
    setAgentRolePrompt(
      "Use Alexandria-Hermes context, skills, and prompts before asking for external research.",
    );
  }

  function editLibrarianAgent(agent: AgentDTO) {
    setEditingAgentId(agent.id);
    setPendingAgentDelete(null);
    setAgentProviderId(agent.preferredLibrarianProvider ?? "");
    setAgentName(agent.name);
    setAgentModel(agent.preferredLibrarianModel ?? "gpt-5.5");
    setAgentRole(agent.librarianRole);
    setAgentMaxCount(agent.maxLibrarianAgents);
    setAgentSpecialties(
      agent.librarianSpecialties.length > 0
        ? agent.librarianSpecialties.join(", ")
        : agent.capabilities.length > 0
        ? agent.capabilities.join(", ")
        : defaultAgentSpecialties,
    );
    setAgentRolePrompt(agent.librarianRolePrompt ?? agent.description ?? "");
  }

  function requestDeleteLibrarianAgent(agent: AgentDTO) {
    setPendingAgentDelete(agent);
  }

  function confirmDeleteLibrarianAgent() {
    if (!pendingAgentDelete) return;
    deleteAgentMutation.mutate({ agentId: pendingAgentDelete.id });
  }

  function handleCreateLibrarianAgent() {
    const providerId = selectedAgentProviderId;
    const name = agentName.trim();
    const rolePrompt = agentRolePrompt.trim();
    if (!providerId || !name || !agentModel.trim() || !rolePrompt) {
      setStatusMessage(t(language, "librarianAgentRequired"));
      return;
    }
    if (!selectedAgentProviderAssignable) {
      setStatusMessage(t(language, "librarianProviderMustBeAuthorized"));
      return;
    }
    const payload: AgentCreateDTO = {
      name,
      provider: "OPENAI_CODEX",
      description: rolePrompt,
      capabilities: specialtiesFromText(agentSpecialties),
      preferredLibrarianProvider: providerId,
      preferredLibrarianModel: agentModel.trim(),
      maxLibrarianAgents: agentMaxCount,
      librarianRolePrompt: rolePrompt,
      librarianRole: agentRole,
      librarianSpecialties: specialtiesFromText(agentSpecialties),
      librarianRoutingPriority: agentRole === "SPECIALIST" ? 20 : 100,
      librarianEnabled: true,
    };
    if (editingAgentId) {
      updateAgentMutation.mutate({ agentId: editingAgentId, payload });
      return;
    }
    createAgentMutation.mutate(payload);
  }

  function updateOAuthStatusMessage(result: LibrarianOAuthStatusDTO) {
    setStatusMessage(
      formatMessage(t(language, "oauthStatusUpdated"), {
        status: result.status,
      }),
    );
  }

  async function pollOAuthUntilTerminal(
    providerId: string,
    intervalSeconds: number,
  ): Promise<LibrarianOAuthStatusDTO> {
    let delayMs = Math.max(
      intervalSeconds * 1000,
      oauthAutoPollMinimumDelayMs,
    );
    for (let attempt = 0; attempt < oauthAutoPollMaxAttempts; attempt += 1) {
      await wait(delayMs);
      const result = await pollLibrarianOAuth(providerId);
      if (isOAuthTerminalStatus(result)) {
        return result;
      }
      if (result.status === "slow_down") {
        delayMs += oauthAutoPollMinimumDelayMs;
      }
    }
    return fetchLibrarianOAuthStatus(providerId);
  }

  function startOAuthAutoPoll(providerId: string, intervalSeconds: number) {
    void pollOAuthUntilTerminal(providerId, intervalSeconds)
      .then((result) => {
        updateOAuthStatusMessage(result);
        void queryClient.invalidateQueries({ queryKey: ["librarian-providers"] });
        void queryClient.invalidateQueries({ queryKey: ["librarian-oauth-statuses"] });
      })
      .catch(() => setStatusMessage(t(language, "oauthActionFailed")));
  }

  return (
    <div className="archive-document-page px-8 py-10 md:px-14 xl:px-16">
      <div className="space-y-7">
        <section className="border-b border-[#cfc8b8] pb-10">
          <p className="text-xs font-bold uppercase tracking-[0.22em] text-[#161616]">{t(language, "settings")}</p>
          <h2 className="mt-5 font-serif text-6xl leading-none tracking-[-0.04em] text-[#070707] md:text-7xl">{t(language, "settingsTitle")}</h2>
          <p className="mt-6 max-w-2xl text-sm leading-7 text-[#36322d]">
            {t(language, "settingsDescription")}
          </p>
        </section>

      {section === "library" || section === "librarians" ? (
        <section id="librarians" className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        {section === "library" ? (
          <>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <KeyRound className="h-5 w-5" /> {t(language, "addLibrarianAuth")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-5" onSubmit={handleCreateProvider}>
              <div className="grid gap-3 md:grid-cols-3">
                <ProviderOption
                  active={providerType === "OPENAI"}
                  icon={Sparkles}
                  title="OpenAI"
                  description={t(language, "openaiProviderDescription")}
                  onClick={() => {
                    setProviderType("OPENAI");
                    setProviderName("");
                    setCredential("");
                  }}
                />
                <ProviderOption
                  active={providerType === "OPENAI_CODEX"}
                  icon={Plug}
                  title="ChatGPT / Codex OAuth"
                  description={t(language, "codexProviderDescription")}
                  onClick={() => {
                    setProviderType("OPENAI_CODEX");
                    setProviderName(t(language, "codexDefaultProviderName"));
                    setCredential("");
                  }}
                />
                <ProviderOption
                  active={providerType === "MINIO"}
                  icon={Cloud}
                  title={t(language, "objectStorageProviderTitle")}
                  description={t(language, "minioProviderDescription")}
                  onClick={() => {
                    setProviderType("MINIO");
                    setProviderName("");
                    setCredential("");
                  }}
                />
              </div>

              <label className={fieldClassName}>
                {t(language, "displayName")}
                <Input
                  name="providerName"
                  autoComplete="organization"
                  value={providerName}
                  placeholder={
                    providerType === "MINIO"
                      ? "Team external archive"
                      : providerType === "OPENAI_CODEX"
                        ? "Codex OAuth librarian"
                        : "OpenAI librarian"
                  }
                  onChange={(event) => setProviderName(event.target.value)}
                />
                <p className={helperClassName}>{t(language, "providerNameHelper")}</p>
              </label>

              <div className="grid gap-6 md:grid-cols-2">
                <div className={fieldClassName}>
                  <span>{t(language, "authMethod")}</span>
                  <div className="rounded-md border border-[#cfc8b8] bg-white/80 px-3 py-2 text-sm font-medium text-[#111111]">
                    {credentialLabel(language, authType, providerType)}
                  </div>
                  <p className={helperClassName}>
                    {providerType === "OPENAI_CODEX"
                      ? t(language, "codexOAuthHelper")
                      : providerType === "OPENAI"
                        ? t(language, "openaiOAuthNotForApi")
                        : t(language, "minioApiKeyHelper")}
                  </p>
                </div>
                {!isOAuthProvider ? (
                  <label className={fieldClassName}>
                    {credentialLabel(language, authType, providerType)}
                    <Input
                      name="credential"
                      autoComplete="off"
                      type="password"
                      value={credential}
                      placeholder={providerType === "MINIO" ? "accessKey:secretKey" : "sk-…"}
                      onChange={(event) => setCredential(event.target.value)}
                    />
                    <p className={helperClassName}>{t(language, "credentialStoredOnly")}</p>
                  </label>
                ) : null}
              </div>

              {providerType === "MINIO" ? (
                <div className="space-y-3">
                  <div className="grid gap-3 md:grid-cols-2">
                    <label className={fieldClassName}>
                      {t(language, "minioEndpoint")}
                      <Input
                        name="minioEndpoint"
                        autoComplete="url"
                        value={minioEndpoint}
                        placeholder={t(language, "minioEndpointPlaceholder")}
                        onChange={(event) => setMinioEndpoint(event.target.value)}
                      />
                    </label>
                    <label className={fieldClassName}>
                      {t(language, "minioBucket")}
                      <Input
                        name="minioBucket"
                        autoComplete="off"
                        value={minioBucket}
                        placeholder={t(language, "minioBucketPlaceholder")}
                        onChange={(event) => setMinioBucket(event.target.value)}
                      />
                    </label>
                    <label className={fieldClassName}>
                      {t(language, "minioPrefix")}
                      <Input
                        name="minioPrefix"
                        autoComplete="off"
                        value={minioPrefix}
                        placeholder={t(language, "minioPrefixPlaceholder")}
                        onChange={(event) => setMinioPrefix(event.target.value)}
                      />
                    </label>
                    <label className={fieldClassName}>
                      {t(language, "minioRegion")}
                      <Input
                        name="minioRegion"
                        autoComplete="off"
                        value={minioRegion}
                        onChange={(event) => setMinioRegion(event.target.value)}
                      />
                    </label>
                  </div>
                  <label className="flex items-center gap-3 rounded-xl border border-[#d8d3c7] bg-white/60 p-3 text-sm font-medium text-[#28241f]">
                    <input
                      name="minioUseSsl"
                      type="checkbox"
                      checked={minioUseSsl}
                      onChange={(event) => setMinioUseSsl(event.target.checked)}
                    />
                    {t(language, "minioUseSsl")}
                  </label>
                  <p className="rounded-xl border border-[#d8d3c7] bg-[#f6f3ec] p-3 text-xs leading-5 text-[#514c44]">
                    {t(language, "minioPlacementHint")}
                  </p>
                </div>
              ) : providerType === "OPENAI_CODEX" ? (
                <p className="rounded-xl border border-[#d8d3c7] bg-white/60 p-3 text-xs leading-5 text-[#514c44]">
                  {t(language, "oauthNoBrowserToken")}
                </p>
              ) : (
                <div className="grid gap-3 md:grid-cols-2">
                  <label className={fieldClassName}>
                    {t(language, "model")}
                    <Input
                      name="model"
                      autoComplete="off"
                      value={model}
                      onChange={(event) => setModel(event.target.value)}
                    />
                  </label>
                  <label className={fieldClassName}>
                    {t(language, "baseUrlOptional")}
                    <Input
                      name="baseUrl"
                      autoComplete="url"
                      value={baseUrl}
                      placeholder="https://api.example.com/v1"
                      onChange={(event) => setBaseUrl(event.target.value)}
                    />
                  </label>
                </div>
              )}

              <label className="flex items-center gap-3 rounded-xl border border-[#d8d3c7] bg-white/60 p-3 text-sm font-medium text-[#28241f]">
                <input
                  name="enabled"
                  type="checkbox"
                  checked={enabled}
                  onChange={(event) => setEnabled(event.target.checked)}
                />
                {t(language, "showAfterSave")}
              </label>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-xs leading-5 text-[#6f6a60]">
                  {providerType === "MINIO"
                    ? t(language, "minioRequiredFields")
                    : providerType === "OPENAI_CODEX"
                      ? t(language, "codexOneClickHint")
                      : t(language, "openaiApiKeyRequired")}
                </p>
                <Button type="submit" disabled={isSavingProvider}>
                  {isSavingProvider
                    ? t(language, "saving")
                    : providerType === "OPENAI_CODEX"
                      ? t(language, "connectCodexOAuth")
                      : t(language, "saveLibrarianAuth")}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t(language, "configuredLibrarians")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {providersQuery.isLoading ? (
              <p className="text-sm text-[#514c44]">{t(language, "loadingLibrarians")}</p>
            ) : providersQuery.isError ? (
              <p className="text-sm text-[#8f5037]">{t(language, "librarianLoadFailed")}</p>
            ) : providersQuery.data?.length ? (
              <>
                {pendingProviderDelete ? (
                  <div className="archive-inline-confirm" role="status" aria-live="polite">
                    <div>
                      <p className="font-semibold text-[#111111]">
                        {formatMessage(t(language, "providerDeleteConfirm"), {
                          name: pendingProviderDelete.name,
                        })}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => setPendingProviderDelete(null)}
                        disabled={deleteProviderMutation.isPending}
                      >
                        {t(language, "cancel")}
                      </Button>
                      <Button
                        type="button"
                        onClick={confirmDeleteProvider}
                        disabled={deleteProviderMutation.isPending}
                      >
                        <Trash2 className="h-4 w-4" aria-hidden />
                        {deleteProviderMutation.isPending
                          ? t(language, "deletingProvider")
                          : t(language, "deleteProvider")}
                      </Button>
                    </div>
                  </div>
                ) : null}
                {oauthDeviceInstruction ? (
                  <div className="rounded-xl border border-[#111111] bg-[#f6f3ec] p-4" role="status" aria-live="polite">
                    <p className="text-sm font-semibold text-[#111111]">
                      {t(language, "oauthDeviceCodeTitle")}
                    </p>
                    <div className="mt-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                      <code className="rounded-lg border border-[#cfc8b8] bg-white px-4 py-3 text-2xl font-bold tracking-[0.22em] text-[#111111]">
                        {oauthDeviceInstruction.userCode}
                      </code>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={() => {
                            void navigator.clipboard.writeText(oauthDeviceInstruction.userCode);
                          }}
                        >
                          {t(language, "copyCode")}
                        </Button>
                        <Button
                          type="button"
                          onClick={() => openOAuthAuthorization(oauthDeviceInstruction.authorizationUrl, null)}
                        >
                          {t(language, "openAuthorizationPage")}
                        </Button>
                      </div>
                    </div>
                    <p className="mt-3 text-xs leading-5 text-[#514c44]">
                      {formatMessage(t(language, "oauthDeviceCodeHelper"), {
                        seconds: String(oauthDeviceInstruction.intervalSeconds),
                      })}
                    </p>
                  </div>
                ) : null}
                {providersQuery.data.map((provider) => (
                  <div key={provider.id} className="rounded-xl border border-[#d8d3c7] bg-white/60 p-4">
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <p className="font-medium text-[#111111]">{provider.name}</p>
                        <p className="mt-1 text-xs uppercase tracking-[0.2em] text-[#6f6a60]">
                          {provider.providerType} · {credentialLabel(language, provider.authType, provider.providerType)}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {provider.providerType === "OPENAI_CODEX" ? (
                          <>
                            <Button
                              type="button"
                              variant="secondary"
                              onClick={() =>
                                oauthActionMutation.mutate({
                                  providerId: provider.id,
                                  action: "start",
                                  popup: prepareOAuthPopup(),
                                })
                              }
                              disabled={oauthActionMutation.isPending}
                            >
                              {t(language, "oauthStart")}
                            </Button>
                            <Button
                              type="button"
                              variant="secondary"
                              onClick={() =>
                                oauthActionMutation.mutate({
                                  providerId: provider.id,
                                  action: "poll",
                                  popup: null,
                                })
                              }
                              disabled={oauthActionMutation.isPending}
                            >
                              {t(language, "oauthPoll")}
                            </Button>
                            <Button
                              type="button"
                              variant="outline"
                              onClick={() =>
                                oauthActionMutation.mutate({
                                  providerId: provider.id,
                                  action: "status",
                                  popup: null,
                                })
                              }
                              disabled={oauthActionMutation.isPending}
                            >
                              {t(language, "oauthStatus")}
                            </Button>
                            <Button
                              type="button"
                              variant="outline"
                              onClick={() =>
                                oauthActionMutation.mutate({
                                  providerId: provider.id,
                                  action: "refresh",
                                  popup: null,
                                })
                              }
                              disabled={oauthActionMutation.isPending}
                            >
                              {t(language, "oauthRefresh")}
                            </Button>
                          </>
                        ) : (
                          <Button
                            type="button"
                            variant="secondary"
                            onClick={() => testProviderMutation.mutate({ providerId: provider.id })}
                            disabled={testProviderMutation.isPending}
                          >
                            {t(language, "verify")}
                          </Button>
                        )}
                        <Button
                          type="button"
                          variant={provider.enabled ? "outline" : "default"}
                          onClick={() =>
                            updateProviderMutation.mutate({
                              providerId: provider.id,
                              nextEnabled: !provider.enabled,
                            })
                          }
                          disabled={updateProviderMutation.isPending}
                        >
                          {provider.enabled ? t(language, "disable") : t(language, "enable")}
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => requestDeleteProvider(provider)}
                          disabled={deleteProviderMutation.isPending}
                        >
                          <Trash2 className="h-4 w-4" aria-hidden />
                          {t(language, "deleteProvider")}
                        </Button>
                      </div>
                    </div>
                    <p className="mt-3 text-sm text-[#514c44]">{configSummary(language, provider.config)}</p>
                    <p className="mt-2 text-xs text-[#6f6a60]">{getProviderStatus(language, provider.enabled)}</p>
                  </div>
                ))}
              </>
            ) : (
              <p className="text-sm text-[#514c44]">
                {t(language, "noLibrarians")}
              </p>
            )}
            {statusMessage ? <p className="text-sm text-[#111111]">{statusMessage}</p> : null}
          </CardContent>
        </Card>

          </>
        ) : null}

        {section === "librarians" ? (
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>{t(language, "librarianAgentProfiles")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm leading-6 text-[#514c44]">
              {t(language, "librarianAgentProfileDescription")}
            </p>
            <div className="space-y-5">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#6f6a60]">
                  {t(language, "librarianProfileIdentity")}
                </p>
                <div className="mt-3 grid gap-6 md:grid-cols-2">
                  <label className={fieldClassName}>
                    {t(language, "librarianProviderConnection")}
                    <select
                      className={`${selectClassName} w-full min-w-[220px]`}
                      value={selectedAgentProviderId}
                      onChange={(event) => setAgentProviderId(event.target.value)}
                      disabled={oauthProviders.length === 0}
                    >
                      {oauthProviders.length === 0 ? (
                        <option value="">{t(language, "noCodexProvider")}</option>
                      ) : null}
                      {oauthProviders.map((provider) => (
                        <option
                          key={provider.id}
                          value={provider.id}
                          disabled={!assignableOAuthProviderIds.has(provider.id)}
                        >
                          {provider.name}
                          {provider.enabled
                            ? authorizedOAuthProviderIds.has(provider.id)
                              ? ""
                              : ` · ${t(language, "oauthNotAuthorized")}`
                            : ` · ${t(language, "providerDisabled")}`}
                        </option>
                      ))}
                    </select>
                    <p className={helperClassName}>
                      {selectedAgentProviderAssignable
                        ? t(language, "oauthAuthorizedForProfile")
                        : t(language, "librarianProviderMustBeAuthorized")}
                    </p>
                  </label>
                  <label className={fieldClassName}>
                    {t(language, "librarianAgentName")}
                    <Input
                      value={agentName}
                      onChange={(event) => setAgentName(event.target.value)}
                    />
                  </label>
                  <label className={fieldClassName}>
                    {t(language, "librarianModel")}
                    <select
                      className={`${selectClassName} w-full min-w-[220px]`}
                      value={agentModel}
                      onChange={(event) => setAgentModel(event.target.value)}
                    >
                      {librarianModelOptions.map((modelOption) => (
                        <option key={modelOption} value={modelOption}>
                          {modelOption}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#6f6a60]">
                  {t(language, "librarianProfileBehavior")}
                </p>
                <div className="mt-3 grid gap-6 md:grid-cols-2">
                  <label className={fieldClassName}>
                    Role
                    <select
                      className={`${selectClassName} w-full min-w-[220px]`}
                      value={agentRole}
                      onChange={(event) =>
                        setAgentRole(event.target.value as LibrarianProfileRole)
                      }
                    >
                      {librarianProfileRoles.map((role) => (
                        <option key={role} value={role}>
                          {role}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className={fieldClassName}>
                    {t(language, "librarianSpecialties")}
                    <Input
                      value={agentSpecialties}
                      onChange={(event) => setAgentSpecialties(event.target.value)}
                      placeholder="library-search, context-recall, skill-acquisition"
                    />
                    <p className={helperClassName}>{t(language, "librarianSpecialtiesHelper")}</p>
                  </label>
                </div>
              </div>
              <details className="rounded-xl border border-[#d8d3c7] bg-white/60 p-4">
                <summary className="cursor-pointer text-sm font-bold text-[#111111]">
                  {t(language, "librarianExecutionPolicy")}
                </summary>
                <label className={`${fieldClassName} mt-4 block max-w-xs`}>
                  {t(language, "maxLibrarianAgents")}
                  <Input
                    type="number"
                    min={1}
                    max={6}
                    value={agentMaxCount}
                    onChange={(event) =>
                      setAgentMaxCount(boundedAgentCount(event.target.value))
                    }
                  />
                  <p className={helperClassName}>{t(language, "maxLibrarianAgentsHelper")}</p>
                </label>
              </details>
            </div>
            <label className={fieldClassName}>
              {t(language, "librarianRolePrompt")}
              <textarea
                className="min-h-28 w-full rounded-sm border border-[#cfc8b8] bg-white/70 px-3 py-2 text-sm text-[#111111] placeholder:text-[#8d8578] outline-none transition-colors hover:border-[#a39b8d] focus-visible:border-[#111111] focus-visible:ring-2 focus-visible:ring-[#111111]/10"
                value={agentRolePrompt}
                onChange={(event) => setAgentRolePrompt(event.target.value)}
              />
              <p className={helperClassName}>{t(language, "librarianRolePromptHelper")}</p>
            </label>
            <Button
              type="button"
              onClick={handleCreateLibrarianAgent}
              disabled={
                oauthProviders.length === 0 ||
                !selectedAgentProviderAssignable ||
                createAgentMutation.isPending ||
                updateAgentMutation.isPending
              }
            >
              {createAgentMutation.isPending || updateAgentMutation.isPending
                ? t(language, "saving")
                : editingAgentId
                  ? t(language, "updateLibrarianAgent")
                  : t(language, "saveLibrarianAgent")}
            </Button>
            {editingAgentId ? (
              <Button type="button" variant="secondary" onClick={resetAgentForm}>
                {t(language, "cancelEditLibrarianAgent")}
              </Button>
            ) : null}
            {statusMessage ? <p className="text-sm text-[#111111]">{statusMessage}</p> : null}
            <div className="space-y-3 border-t border-[#d8d3c7] pt-4">
              <p className="text-sm font-semibold text-[#111111]">
                {t(language, "savedLibrarianAgents")}
              </p>
              {agentsQuery.isLoading ? (
                <p className="text-sm text-[#514c44]">{t(language, "loadingAgents")}</p>
              ) : agentsQuery.isError ? (
                <p className="text-sm text-[#8f5037]">{t(language, "agentLoadFailed")}</p>
              ) : librarianAgents.length ? (
                librarianAgents.map((agent) => (
                  <div key={agent.id} className="rounded-xl border border-[#d8d3c7] bg-white/60 p-4">
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <p className="font-medium text-[#111111]">{agent.name}</p>
                        <p className="mt-1 text-xs uppercase tracking-[0.2em] text-[#6f6a60]">
                          {agent.librarianRole} ·{" "}
                          {agent.preferredLibrarianModel ?? t(language, "modelUnset")}
                        </p>
                        <p className="mt-2 line-clamp-2 text-sm leading-6 text-[#514c44]">
                          {agent.librarianRolePrompt ?? agent.description}
                        </p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {(agent.librarianSpecialties.length > 0
                            ? agent.librarianSpecialties
                            : agent.capabilities
                          ).map((capability) => (
                            <span
                              key={capability}
                              className="rounded-full border border-[#d8d3c7] bg-white px-2.5 py-1 text-xs text-[#514c44]"
                            >
                              {capability}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={() => editLibrarianAgent(agent)}
                        >
                          {t(language, "editLibrarianAgent")}
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => requestDeleteLibrarianAgent(agent)}
                          disabled={deleteAgentMutation.isPending}
                        >
                          <Trash2 className="h-4 w-4" aria-hidden />
                          {t(language, "deleteLibrarianAgent")}
                        </Button>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-[#514c44]">{t(language, "noLibrarianAgents")}</p>
              )}
              {pendingAgentDelete ? (
                <div className="archive-inline-confirm" role="status" aria-live="polite">
                  <p className="font-semibold text-[#111111]">
                    {formatMessage(t(language, "librarianAgentDeleteConfirm"), {
                      name: pendingAgentDelete.name,
                    })}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => setPendingAgentDelete(null)}
                      disabled={deleteAgentMutation.isPending}
                    >
                      {t(language, "cancel")}
                    </Button>
                    <Button
                      type="button"
                      onClick={confirmDeleteLibrarianAgent}
                      disabled={deleteAgentMutation.isPending}
                    >
                      <Trash2 className="h-4 w-4" aria-hidden />
                      {deleteAgentMutation.isPending
                        ? t(language, "deletingProvider")
                        : t(language, "deleteLibrarianAgent")}
                    </Button>
                  </div>
                </div>
              ) : null}
            </div>
          </CardContent>
        </Card>

        ) : null}

        {section === "library" ? (
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>{t(language, "minioImportTitle")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col gap-3 rounded-xl border border-[#d8d3c7] bg-[#f6f3ec] p-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="font-medium text-[#111111]">{t(language, "minioImportHeading")}</p>
                <p className="mt-1 text-sm leading-6 text-[#514c44]">
                  {t(language, "minioImportDescription")}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => void importCandidatesQuery.refetch()}
                  disabled={!hasEnabledMinioProvider || importCandidatesQuery.isFetching}
                >
                  {importCandidatesQuery.isFetching ? t(language, "scanning") : t(language, "scanMinio")}
                </Button>
                <Button
                  type="button"
                  onClick={() => importArchiveMutation.mutate()}
                  disabled={!hasEnabledMinioProvider || importArchiveMutation.isPending}
                >
                  {importArchiveMutation.isPending ? t(language, "importing") : t(language, "importMinio")}
                </Button>
              </div>
            </div>
            {!hasEnabledMinioProvider ? (
              <p className="text-sm text-[#6f6a60]">{t(language, "minioImportNeedsProvider")}</p>
            ) : importCandidatesQuery.isError ? (
              <p className="text-sm text-[#8f5037]">{t(language, "minioImportScanFailed")}</p>
            ) : importCandidatesQuery.data?.length ? (
              <div className="grid gap-3 md:grid-cols-2">
                {importCandidatesQuery.data.slice(0, 4).map((candidate) => (
                  <div key={candidate.id} className="rounded-xl border border-[#d8d3c7] bg-white/60 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-medium text-[#111111]">{candidate.title}</p>
                        <p className="mt-1 text-xs uppercase tracking-[0.18em] text-bronze">
                          {candidate.itemType} · {candidate.bucket}
                        </p>
                      </div>
                      <span className="rounded-full border border-[#d8d3c7] px-2 py-1 text-xs text-[#514c44]">
                        {Math.round(candidate.confidence * 100)}%
                      </span>
                    </div>
                    <p className="mt-3 line-clamp-2 text-sm leading-6 text-[#514c44]">
                      {candidate.summary}
                    </p>
                    <p className="mt-2 truncate text-xs text-[#6f6a60]">{candidate.objectKey}</p>
                  </div>
                ))}
              </div>
            ) : importCandidatesQuery.data ? (
              <p className="text-sm text-[#514c44]">{t(language, "minioImportNoCandidates")}</p>
            ) : (
              <p className="text-sm text-[#6f6a60]">{t(language, "minioImportNotScanned")}</p>
            )}
          </CardContent>
        </Card>
        ) : null}
        </section>
      ) : null}

      {section === "library" ? (
        <section id="library" className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5" aria-hidden="true" /> Hermes Integration
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm leading-6 text-[#514c44]">
              Install Alexandria prompts and the library skill with <code>alexandria-hermes hermes onboard --dry-run</code> before writing into a Hermes home folder.
            </p>
            <div className="rounded-xl border border-[#d8d3c7] bg-white/60 p-3 text-xs leading-5 text-[#36322d]">
              Path order: command flag → HERMES_HOME → saved config → ~/.hermes → required-home error.
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Plug className="h-5 w-5" aria-hidden="true" /> MCP Status
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm leading-6 text-[#514c44]">
              MCP clients can launch <code>alexandria-hermes mcp serve</code> and use HTTP-only tools for search, recall, capture, compact, archive, and RAG health.
            </p>
            <pre className="overflow-auto rounded-xl border border-[#d8d3c7] bg-white/60 p-3 text-xs text-[#36322d]">{`{\"mcpServers\":{\"alexandria\":{\"command\":\"alexandria-hermes\",\"args\":[\"mcp\",\"serve\"]}}}`}</pre>
          </CardContent>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Gauge className="h-5 w-5" aria-hidden="true" /> RAG Status
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-3">
            {(["fts", "vector", "embedding"] as const).map((key) => (
              <div key={key} className="rounded-xl border border-[#d8d3c7] bg-white/60 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-[#6f6a60]">{key}</p>
                <p className="mt-2 font-serif text-2xl text-[#111111]">
                  {ragStatusQuery.data ? ragStatusQuery.data[key] : "Checking…"}
                </p>
              </div>
            ))}
            {ragStatusQuery.data?.warnings.length ? (
              <p className="md:col-span-3 text-sm leading-6 text-[#8f5037]">
                {ragStatusQuery.data.warnings.join(" · ")}
              </p>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <SlidersHorizontal className="h-5 w-5" /> {t(language, "librarySettings")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col gap-3 rounded-xl border border-[#d8d3c7] bg-white/60 p-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="font-medium text-[#111111]">{t(language, "defaultView")}</p>
                <p className="text-sm text-[#6f6a60]">{t(language, "defaultViewDescription")}</p>
              </div>
              <div className="flex gap-2">
                <Button
                  variant={viewMode === "grid" ? "default" : "secondary"}
                  aria-pressed={viewMode === "grid"}
                  onClick={() => setViewMode("grid")}
                >
                  {t(language, "card")}
                </Button>
                <Button
                  variant={viewMode === "list" ? "default" : "secondary"}
                  aria-pressed={viewMode === "list"}
                  onClick={() => setViewMode("list")}
                >
                  {t(language, "list")}
                </Button>
              </div>
            </div>
            <div className="flex flex-col gap-3 rounded-xl border border-[#d8d3c7] bg-white/60 p-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="font-medium text-[#111111]">{t(language, "resetFilters")}</p>
                <p className="text-sm text-[#6f6a60]">{t(language, "resetFiltersDescription")}</p>
              </div>
              <Button variant="outline" onClick={clearFilters}>{t(language, "resetFilterButton")}</Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t(language, "screenSettings")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col gap-3 rounded-xl border border-[#d8d3c7] bg-white/60 p-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="font-medium text-[#111111]">{t(language, "sidebar")}</p>
                <p className="text-sm text-[#6f6a60]">{t(language, "sidebarDescription")}</p>
              </div>
              <Button variant="secondary" onClick={() => setCollapsed(!collapsed)}>
                <PanelLeftClose className="h-4 w-4" /> {collapsed ? t(language, "expand") : t(language, "collapse")}
              </Button>
            </div>
            <div className="flex flex-col gap-3 rounded-xl border border-[#d8d3c7] bg-white/60 p-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="font-medium text-[#111111]">{t(language, "language")}</p>
                <p className="text-sm text-[#6f6a60]">{t(language, "languageDescription")}</p>
              </div>
              <div className="flex gap-2">
                {languageOptions.map((option) => (
                  <Button
                    key={option.value}
                    variant={language === option.value ? "default" : "secondary"}
                    aria-pressed={language === option.value}
                    onClick={() => setLanguage(option.value as Language)}
                  >
                    <Languages className="h-4 w-4" /> {option.label}
                  </Button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
        </section>
      ) : null}
      </div>
    </div>
  );
}
