import type { CollectionRun, Comparison, Product, Source, Variant } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      Accept: "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail =
      payload && typeof payload.detail === "string" ? payload.detail : response.statusText;
    throw new Error(detail || `Falha HTTP ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  listSources: () => request<Source[]>("/sources"),
  listProducts: () => request<Product[]>("/products"),
  listVariants: (productId: string) => request<Variant[]>(`/products/${productId}/variants`),
  getComparison: (variantId: string) => request<Comparison>(`/variants/${variantId}/comparison`),
  collectSource: (sourceId: string) =>
    request<CollectionRun>(`/sources/${sourceId}/collect`, { method: "POST" }),
  getRun: (runId: string) => request<CollectionRun>(`/runs/${runId}`),
};
