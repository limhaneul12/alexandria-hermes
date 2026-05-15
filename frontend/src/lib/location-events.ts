export const LOCATION_CHANGE_EVENT = "alexandria:location-change";

let installCount = 0;
let originalPushState: History["pushState"] | null = null;
let originalReplaceState: History["replaceState"] | null = null;

function emitLocationChange() {
  window.dispatchEvent(new Event(LOCATION_CHANGE_EVENT));
}

export function readLocationHash() {
  if (typeof window === "undefined") return "";
  return window.location.hash;
}

export function installLocationChangeEvents() {
  if (typeof window === "undefined") return () => undefined;

  installCount += 1;
  if (installCount === 1) {
    originalPushState = window.history.pushState;
    originalReplaceState = window.history.replaceState;

    window.history.pushState = function pushState(
      this: History,
      ...args: Parameters<History["pushState"]>
    ): void {
      originalPushState?.apply(this, args);
      emitLocationChange();
    };

    window.history.replaceState = function replaceState(
      this: History,
      ...args: Parameters<History["replaceState"]>
    ): void {
      originalReplaceState?.apply(this, args);
      emitLocationChange();
    };
  }

  return () => {
    installCount = Math.max(0, installCount - 1);
    if (installCount !== 0) return;
    if (originalPushState) window.history.pushState = originalPushState;
    if (originalReplaceState) window.history.replaceState = originalReplaceState;
    originalPushState = null;
    originalReplaceState = null;
  };
}
