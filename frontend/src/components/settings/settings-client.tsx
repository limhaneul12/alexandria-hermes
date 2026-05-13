"use client";

import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Moon, PanelLeftClose, SlidersHorizontal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  createLibrarianProvider,
  fetchLibrarianProviders,
  testLibrarianProvider,
  updateLibrarianProvider,
} from "@/lib/api";
import { useLibraryStore } from "@/store/library-store";
import {
  PROVIDER_TYPES,
  type AuthType,
  type LibrarianProviderCreateDTO,
  type LibrarianProviderCredentialMode,
  type ProviderType,
} from "@/types/library";

const selectClassName =
  "h-10 rounded-md border border-white/10 bg-black/30 px-3 py-2 text-sm text-parchment outline-none transition focus:border-gold-300/50 focus:ring-1 focus:ring-gold-300/30";

function credentialLabel(authType: AuthType) {
  if (authType === "OAUTH") return "OAuth access token (추후 지원)";
  if (authType === "NONE") return "인증 없음";
  return "API key";
}

function configSummary(config: Record<string, unknown>) {
  const entries = Object.entries(config).filter(([, value]) => value !== "" && value !== undefined);
  if (entries.length === 0) return "추가 설정 없음";
  return entries.map(([key, value]) => `${key}: ${String(value)}`).join(" · ");
}

export function SettingsClient() {
  const queryClient = useQueryClient();
  const collapsed = useLibraryStore((state) => state.sidebarCollapsed);
  const setCollapsed = useLibraryStore((state) => state.setSidebarCollapsed);
  const theme = useLibraryStore((state) => state.theme);
  const setTheme = useLibraryStore((state) => state.setTheme);
  const viewMode = useLibraryStore((state) => state.viewMode);
  const setViewMode = useLibraryStore((state) => state.setViewMode);
  const clearFilters = useLibraryStore((state) => state.clearFilters);

  const [providerName, setProviderName] = useState("default-openai");
  const [providerType, setProviderType] = useState<ProviderType>("OPENAI");
  const [authType] = useState<LibrarianProviderCredentialMode>("API_KEY");
  const [credential, setCredential] = useState("");
  const [model, setModel] = useState("gpt-5.5");
  const [baseUrl, setBaseUrl] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isSavingProvider, setIsSavingProvider] = useState(false);

  const providersQuery = useQuery({
    queryKey: ["librarian-providers"],
    queryFn: fetchLibrarianProviders,
  });

  const providerConfig = useMemo(() => {
    const config: Record<string, unknown> = {};
    if (model.trim()) config.model = model.trim();
    if (baseUrl.trim()) config.base_url = baseUrl.trim();
    return config;
  }, [baseUrl, model]);

  const updateProviderMutation = useMutation({
    mutationFn: ({ providerId, nextEnabled }: { providerId: string; nextEnabled: boolean }) =>
      updateLibrarianProvider(providerId, { enabled: nextEnabled }),
    onSuccess: async (provider) => {
      setStatusMessage(`${provider.name} 사서 인증 상태를 업데이트했습니다.`);
      await queryClient.invalidateQueries({ queryKey: ["librarian-providers"] });
    },
    onError: () => setStatusMessage("사서 인증 상태 변경에 실패했습니다."),
  });

  const testProviderMutation = useMutation({
    mutationFn: ({ providerId }: { providerId: string }) => testLibrarianProvider(providerId, "ping"),
    onSuccess: (result) => {
      setStatusMessage(result.ok ? result.message : `검증 실패: ${result.message}`);
    },
    onError: () => setStatusMessage("사서 인증 검증 요청에 실패했습니다."),
  });

  async function handleCreateProvider(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedName = providerName.trim();
    const trimmedCredential = credential.trim();
    if (!trimmedName || !trimmedCredential) {
      setStatusMessage("이름과 인증값을 입력해야 합니다.");
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
      setStatusMessage(`${provider.name} 사서 인증이 저장되었습니다.`);
      await queryClient.invalidateQueries({ queryKey: ["librarian-providers"] });
    } catch {
      setStatusMessage("사서 인증 저장에 실패했습니다. 인증값과 설정을 확인하세요.");
    } finally {
      setIsSavingProvider(false);
    }
  }

  return (
    <div className="space-y-7">
      <section className="rounded-3xl border border-gold-300/20 bg-archive-panel p-8 shadow-gold">
        <p className="text-xs uppercase tracking-[0.34em] text-bronze">Settings</p>
        <h2 className="mt-3 font-serif text-5xl text-gold-50">서재 사용 환경</h2>
        <p className="mt-4 max-w-2xl text-base leading-7 text-stone-300">
          화면 밀도, 탐색 방식, 사이드바 상태와 에이전트가 사용할 서재 관리 사서를 관리합니다.
        </p>
      </section>

      <section id="librarians" className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <KeyRound className="h-5 w-5" /> 사서 인증 추가
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleCreateProvider}>
              <div className="grid gap-3 md:grid-cols-2">
                <label className="space-y-2 text-sm text-stone-400">
                  표시 이름
                  <Input value={providerName} onChange={(event) => setProviderName(event.target.value)} />
                </label>
                <label className="space-y-2 text-sm text-stone-400">
                  사서 유형
                  <select
                    className={selectClassName}
                    value={providerType}
                    onChange={(event) => setProviderType(event.target.value as ProviderType)}
                  >
                    {PROVIDER_TYPES.map((type) => (
                      <option key={type} value={type}>{type}</option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <label className="space-y-2 text-sm text-stone-400">
                  인증 방식
                  <select className={selectClassName} value={authType} disabled>
                    <option value="API_KEY">API key</option>
                  </select>
                  <p className="text-xs leading-5 text-stone-500">
                    OAuth 계정 인증은 다음 slice에서 PKCE/state 기반으로 안전하게 추가합니다.
                  </p>
                </label>
                <label className="space-y-2 text-sm text-stone-400">
                  {credentialLabel(authType)}
                  <Input
                    autoComplete="off"
                    type="password"
                    value={credential}
                    placeholder="sk-..."
                    onChange={(event) => setCredential(event.target.value)}
                  />
                </label>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <label className="space-y-2 text-sm text-stone-400">
                  모델
                  <Input value={model} onChange={(event) => setModel(event.target.value)} />
                </label>
                <label className="space-y-2 text-sm text-stone-400">
                  Base URL (선택)
                  <Input
                    value={baseUrl}
                    placeholder="https://api.example.com/v1"
                    onChange={(event) => setBaseUrl(event.target.value)}
                  />
                </label>
              </div>

              <label className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-3 text-sm text-stone-300">
                <input
                  type="checkbox"
                  checked={enabled}
                  onChange={(event) => setEnabled(event.target.checked)}
                />
                저장 후 바로 에이전트 배정 선택지에 표시
              </label>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-xs leading-5 text-stone-500">
                  인증값은 저장 요청에만 사용하고 화면에는 다시 표시하지 않습니다.
                </p>
                <Button type="submit" disabled={isSavingProvider}>
                  {isSavingProvider ? "저장 중" : "사서 인증 저장"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>구성된 서재 관리 사서</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {providersQuery.isLoading ? (
              <p className="text-sm text-stone-400">사서 인증 정보를 불러오는 중입니다.</p>
            ) : providersQuery.isError ? (
              <p className="text-sm text-red-300">사서 인증 목록을 불러오지 못했습니다.</p>
            ) : providersQuery.data?.length ? (
              providersQuery.data.map((provider) => (
                <div key={provider.id} className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div>
                      <p className="font-medium text-parchment">{provider.name}</p>
                      <p className="mt-1 text-xs uppercase tracking-[0.2em] text-stone-500">
                        {provider.providerType} · {credentialLabel(provider.authType)}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => testProviderMutation.mutate({ providerId: provider.id })}
                        disabled={testProviderMutation.isPending}
                      >
                        검증
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
                        {provider.enabled ? "비활성화" : "활성화"}
                      </Button>
                    </div>
                  </div>
                  <p className="mt-3 text-sm text-stone-400">{configSummary(provider.config)}</p>
                  <p className="mt-2 text-xs text-stone-500">
                    상태: {provider.enabled ? "에이전트에 할당 가능" : "비활성"}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-sm text-stone-400">
                아직 저장된 서재 관리 사서가 없습니다. API key로 첫 사서 인증을 추가하세요.
              </p>
            )}
            {statusMessage ? <p className="text-sm text-gold-100">{statusMessage}</p> : null}
          </CardContent>
        </Card>
      </section>

      <section id="library" className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><SlidersHorizontal className="h-5 w-5" /> 서재 설정</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="font-medium text-parchment">기본 보기</p>
                <p className="text-sm text-stone-500">책 표지형 카드 또는 목록형으로 서재를 봅니다.</p>
              </div>
              <div className="flex gap-2">
                <Button variant={viewMode === "grid" ? "default" : "secondary"} onClick={() => setViewMode("grid")}>카드</Button>
                <Button variant={viewMode === "list" ? "default" : "secondary"} onClick={() => setViewMode("list")}>목록</Button>
              </div>
            </div>
            <div className="flex flex-col gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="font-medium text-parchment">탐색 조건 초기화</p>
                <p className="text-sm text-stone-500">검색어, 카테고리, 태그, 유형, 정렬 상태를 지웁니다.</p>
              </div>
              <Button variant="outline" onClick={clearFilters}>필터 초기화</Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>화면 설정</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="font-medium text-parchment">사이드바</p>
                <p className="text-sm text-stone-500">서재 탐색 영역을 넓게 쓰고 싶을 때 접습니다.</p>
              </div>
              <Button variant="secondary" onClick={() => setCollapsed(!collapsed)}>
                <PanelLeftClose className="h-4 w-4" /> {collapsed ? "펼치기" : "접기"}
              </Button>
            </div>
            <div className="flex flex-col gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="font-medium text-parchment">화면 톤</p>
                <p className="text-sm text-stone-500">짙은 도서관 톤과 따뜻한 금색 강조를 선택합니다.</p>
              </div>
              <div className="flex gap-2">
                <Button variant={theme === "dark" ? "default" : "secondary"} onClick={() => setTheme("dark")}><Moon className="h-4 w-4" /> 기본</Button>
                <Button variant={theme === "ember" ? "default" : "secondary"} onClick={() => setTheme("ember")}>웜톤</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
