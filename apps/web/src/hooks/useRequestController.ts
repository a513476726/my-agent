import { ref } from "vue";

const pendingControllers = new Map<string, AbortController>();
const handlingUnauthorized = ref(false);

export function useRequestController() {
  function registerRequest(key: string, controller: AbortController): void {
    pendingControllers.set(key, controller);
  }

  function removeRequest(key: string): void {
    pendingControllers.delete(key);
  }

  function cancelAllRequests(reason = "cancelled"): void {
    pendingControllers.forEach((controller) => controller.abort(reason));
    pendingControllers.clear();
  }

  function tryMarkUnauthorized(): boolean {
    if (handlingUnauthorized.value) return false;
    handlingUnauthorized.value = true;
    return true;
  }

  function resetUnauthorized(): void {
    handlingUnauthorized.value = false;
  }

  return {
    registerRequest,
    removeRequest,
    cancelAllRequests,
    tryMarkUnauthorized,
    resetUnauthorized,
    getPendingCount: () => pendingControllers.size,
  };
}
