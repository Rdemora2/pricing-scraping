import type {
  CollectionRun,
  Comparison,
  Product,
  ProductCreatePayload,
  ProductDetail,
  ProductIntelligence,
  Source,
  SourceCandidate,
  Variant,
} from "./types";

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
  listSources: (enabledOnly = true) =>
    request<Source[]>(`/sources?enabled_only=${enabledOnly ? "true" : "false"}`),
  listProducts: () => request<Product[]>("/products"),
  listVariants: (productId: string) => request<Variant[]>(`/products/${productId}/variants`),
  getProductIntelligence: (productId: string) =>
    request<ProductIntelligence>(`/products/${productId}/intelligence`),
  getComparison: (variantId: string) => request<Comparison>(`/variants/${variantId}/comparison`),
  collectSource: (sourceId: string) =>
    request<CollectionRun>(`/sources/${sourceId}/collect`, { method: "POST" }),
  getRun: (runId: string) => request<CollectionRun>(`/runs/${runId}`),
  createProduct: (payload: ProductCreatePayload) =>
    request<ProductDetail>("/products", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  listCandidates: () => request<SourceCandidate[]>("/discovery/candidates"),
  discover: (query: string) =>
    request<SourceCandidate[]>("/discovery/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    }),
  createCandidate: (payload: { url: string; title: string; snippet?: string }) =>
    request<SourceCandidate>("/discovery/candidates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
};
