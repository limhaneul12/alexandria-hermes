export const OPEN_LIBRARIAN_ASK_EVENT = "alexandria:open-librarian-ask";

export type OpenLibrarianAskEventDetail = {
  prompt?: string;
};

export function openLibrarianAsk(prompt?: string) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent<OpenLibrarianAskEventDetail>(OPEN_LIBRARIAN_ASK_EVENT, {
      detail: prompt ? { prompt } : {},
    }),
  );
}
