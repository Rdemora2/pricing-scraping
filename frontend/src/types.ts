export type Source = {
  id: string;
  name: string;
  base_url: string;
  kind: string;
  status: string;
  adapter_name: string;
};

export type SourceCandidate = {
  id: string;
  url: string;
  domain: string;
  title: string;
  snippet: string;
  provider: string;
  query: string;
  trust_tier: "trusted" | "known" | "unknown";
  status: "candidate" | "reviewed" | "rejected";
  discovered_at: string;
};

export type CollectionRun = {
  id: string;
  source_id: string;
  trigger: string;
  status: "pending" | "running" | "succeeded" | "failed" | "partial";
  started_at: string | null;
  finished_at: string | null;
  stats: Record<string, number>;
  failure_reason: string | null;
};

export type Product = {
  id: string;
  name: string;
  brand: string;
  category: string;
};

export type ProductCreatePayload = {
  name: string;
  brand: string;
  category: string;
  variants: Array<{
    attributes: Record<string, string>;
    gtin: string | null;
  }>;
};

export type ProductDetail = {
  product: Product;
  variants: Variant[];
};

export type Variant = {
  id: string;
  product_id: string;
  attributes: Record<string, string>;
  gtin: string | null;
};

export type Offer = {
  offer_id: string;
  source_name: string;
  seller_name: string;
  url: string;
  price: string;
  currency: string;
  condition: string;
  availability: string;
  observed_at: string;
  payment_terms: {
    installment_count: number | null;
    cash_discount_pct: string | null;
    coupon_code: string | null;
    price_basis: "advertised" | "cash" | "installment" | "conditional";
    is_conditional: boolean;
    condition_summary: string | null;
  };
  shipping: {
    known: boolean;
    cost_minor_units: number | null;
    cost_currency: string | null;
    free_shipping_threshold_minor_units: number | null;
  };
};

export type ExcludedOffer = {
  offer_id: string;
  source_name: string;
  seller_name: string;
  reason: string;
};

export type Comparison = {
  variant_id: string;
  currency: string;
  has_comparable_data: boolean;
  included_offer_count: number;
  source_count: number;
  retailer_count: number;
  min_price: string | null;
  median_price: string | null;
  max_price: string | null;
  offers: Offer[];
  excluded: ExcludedOffer[];
  oldest_observation_at: string | null;
  newest_observation_at: string | null;
  freshness_window_hours: number;
  generated_at: string;
};

export type VariantIntelligence = {
  variant_id: string;
  storage_gb: number;
  color: string;
  min_price: string;
  median_price: string;
  max_price: string;
  offer_count: number;
  retailer_count: number;
};

export type StorageIntelligence = {
  storage_gb: number;
  catalog_variant_count: number;
  observed_variant_count: number;
  min_price: string | null;
  representative_price: string | null;
  max_price: string | null;
  price_per_gb: string | null;
};

export type ColorIntelligence = {
  color: string;
  catalog_variant_count: number;
  observed_variant_count: number;
  comparable_storage_count: number;
  min_price: string | null;
  representative_price: string | null;
  max_price: string | null;
  relative_price_delta_pct: string | null;
};

export type ProductIntelligence = {
  product_id: string;
  currency: string;
  catalog_variant_count: number;
  observed_variant_count: number;
  coverage_pct: number;
  total_offer_count: number;
  retailer_count: number;
  sample_status: "no_data" | "limited" | "developing" | "strong";
  storages_gb: number[];
  colors: string[];
  min_price: string | null;
  max_price: string | null;
  cheapest_variant: VariantIntelligence | null;
  most_expensive_variant: VariantIntelligence | null;
  best_value_storage: StorageIntelligence | null;
  cheapest_storage: StorageIntelligence | null;
  most_expensive_storage: StorageIntelligence | null;
  cheapest_color: ColorIntelligence | null;
  most_expensive_color: ColorIntelligence | null;
  storage_analysis: StorageIntelligence[];
  color_analysis: ColorIntelligence[];
  methodology: string[];
  freshness_window_hours: number;
  generated_at: string;
};
