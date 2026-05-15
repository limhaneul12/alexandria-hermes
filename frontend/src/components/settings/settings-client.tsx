"use client";

import { type FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Cloud, Gauge, KeyRound, Languages, PanelLeftClose, Plug, ShieldCheck, SlidersHorizontal, Sparkles, type LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  createLibrarianProvider,
  fetchExternalArchiveCandidates,
  fetchLibrarianProviders,
  fetchRagStatus,
  importExternalArchiveCandidates,
  testLibrarianProvider,
  updateLibrarianProvider,
} from "@/lib/api";
import { languageOptions, t, type Language } from "@/lib/i18n";
import { useLibraryStore } from "@/store/library-store";
import {
  type AuthType,
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

function getSettingsSectionFromHash(): SettingsSection {
  if (typeof window === "undefined") return "library";
  return window.location.hash.replace(/^#/, "") === "librarians" ? "librarians" : "library";
}

function formatMessage(template: string, values: Record<string, string>) {
  return Object.entries(values).reduce(
    (message, [key, value]) => message.replace(`{${key}}`, value),
    template,
  );
}

function credentialLabel(language: Language, authType: AuthType, providerType?: ProviderType) {
  if (providerType === "MINIO") return t(language, "minioCredential");
  if (authType === "OAUTH") return "OAuth access token";
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

export function SettingsClient() {
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
  const [authType] = useState<LibrarianProviderCredentialMode>("API_KEY");
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
  const [isSavingProvider, setIsSavingProvider] = useState(false);
  const [activeSettingsSection, setActiveSettingsSection] = useState<SettingsSection>("library");

  useEffect(() => {
    const updateActiveSection = () => setActiveSettingsSection(getSettingsSectionFromHash());
    updateActiveSection();
    window.addEventListener("hashchange", updateActiveSection);
    window.addEventListener("popstate", updateActiveSection);
    return () => {
      window.removeEventListener("hashchange", updateActiveSection);
      window.removeEventListener("popstate", updateActiveSection);
    };
  }, []);

  const providersQuery = useQuery({
    queryKey: ["librarian-providers"],
    queryFn: fetchLibrarianProviders,
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

  const providerConfig = useMemo(() => {
    const config: Record<string, unknown> = {};
    if (providerType === "MINIO") {
      if (minioEndpoint.trim()) config.endpoint = minioEndpoint.trim();
      if (minioBucket.trim()) config.bucket = minioBucket.trim();
      if (minioPrefix.trim()) config.prefix = minioPrefix.trim();
      if (minioRegion.trim()) config.region = minioRegion.trim();
      config.use_ssl = minioUseSsl;
    } else {
      if (model.trim()) config.model = model.trim();
      if (baseUrl.trim()) config.base_url = baseUrl.trim();
    }
    return config;
  }, [baseUrl, minioBucket, minioEndpoint, minioPrefix, minioRegion, minioUseSsl, model, providerType]);

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
    const trimmedName = providerName.trim();
    const trimmedCredential = credential.trim();
    if (!trimmedName || !trimmedCredential) {
      setStatusMessage(t(language, "nameAndCredentialRequired"));
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
      credential: trimmedCredential,
    };
    setCredential("");
    setIsSavingProvider(true);
    try {
      const provider = await createLibrarianProvider(payload);
      setStatusMessage(formatMessage(t(language, "providerSaved"), { name: provider.name }));
      queryClient.setQueryData<LibrarianProviderDTO[]>(["librarian-providers"], (providers) =>
        upsertProvider(providers, provider),
      );
      void queryClient.invalidateQueries({ queryKey: ["librarian-providers"] });
    } catch {
      setStatusMessage(t(language, "providerSaveFailed"));
    } finally {
      setIsSavingProvider(false);
    }
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

      {activeSettingsSection === "librarians" ? (
        <section id="librarians" className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <KeyRound className="h-5 w-5" /> {t(language, "addLibrarianAuth")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-5" onSubmit={handleCreateProvider}>
              <div className="grid gap-3 md:grid-cols-2">
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
                  active={providerType === "MINIO"}
                  icon={Cloud}
                  title="MINIO"
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
                  placeholder={providerType === "MINIO" ? "Team MinIO archive" : "OpenAI librarian"}
                  onChange={(event) => setProviderName(event.target.value)}
                />
                <p className={helperClassName}>{t(language, "providerNameHelper")}</p>
              </label>

              <div className="grid gap-3 md:grid-cols-2">
                <label className={fieldClassName}>
                  {t(language, "authMethod")}
                  <select name="authType" className={selectClassName} value={authType} disabled>
                    <option value="API_KEY">{t(language, "apiKey")}</option>
                  </select>
                  <p className={helperClassName}>
                    {providerType === "OPENAI" ? t(language, "openaiOAuthNotForApi") : t(language, "minioApiKeyHelper")}
                  </p>
                </label>
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
                  {providerType === "MINIO" ? t(language, "minioRequiredFields") : t(language, "openaiApiKeyRequired")}
                </p>
                <Button type="submit" disabled={isSavingProvider}>
                  {isSavingProvider ? t(language, "saving") : t(language, "saveLibrarianAuth")}
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
              providersQuery.data.map((provider) => (
                <div key={provider.id} className="rounded-xl border border-[#d8d3c7] bg-white/60 p-4">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div>
                      <p className="font-medium text-[#111111]">{provider.name}</p>
                      <p className="mt-1 text-xs uppercase tracking-[0.2em] text-[#6f6a60]">
                        {provider.providerType} · {credentialLabel(language, provider.authType, provider.providerType)}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => testProviderMutation.mutate({ providerId: provider.id })}
                        disabled={testProviderMutation.isPending}
                      >
                        {t(language, "verify")}
                      </Button>
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
                    </div>
                  </div>
                  <p className="mt-3 text-sm text-[#514c44]">{configSummary(language, provider.config)}</p>
                  <p className="mt-2 text-xs text-[#6f6a60]">{getProviderStatus(language, provider.enabled)}</p>
                </div>
              ))
            ) : (
              <p className="text-sm text-[#514c44]">
                {t(language, "noLibrarians")}
              </p>
            )}
            {statusMessage ? <p className="text-sm text-[#111111]">{statusMessage}</p> : null}
          </CardContent>
        </Card>

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
        </section>
      ) : null}

      {activeSettingsSection === "library" ? (
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
