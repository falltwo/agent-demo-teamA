import { ref } from "vue";

export type ToastVariant = "error" | "info";

export interface ToastEntry {
  id: number;
  variant: ToastVariant;
  code?: string;
  message: string;
  details?: unknown;
}

const items = ref<ToastEntry[]>([]);
let nextId = 0;

export function toastItems() {
  return items;
}

export function pushToast(entry: Omit<ToastEntry, "id">): number {
  const id = ++nextId;
  items.value = [...items.value, { ...entry, id }];
  window.setTimeout(() => dismissToast(id), 7000);
  return id;
}

export function dismissToast(id: number) {
  items.value = items.value.filter((x) => x.id !== id);
}
