import { useCallback, useEffect, useMemo, useState } from "react";

import { api } from "./api";
import { ProductIntelligencePanel } from "./components/ProductIntelligencePanel";
import { formatDate, formatMoney } from "./formatters";
import type {
  CollectionRun,
  Comparison,
  Product,
  ProductIntelligence,
  Source,
  SourceCandidate,
  Variant,
} from "./types";

type View = "overview" | "catalog" | "sources" | "discovery";
type IconName = "arrow" | "bolt" | "check" | "database" | "signal" | "grid" | "search" | "plus";

const terminalStatuses = new Set<CollectionRun["status"]>(["succeeded", "failed", "partial"]);
const priorityVariantByProduct: Record<string, { storage: string; color: string }> = {
  "Apple iPhone 17": { storage: "256", color: "Preto" },
  "Apple iPhone 17 Pro": { storage: "256", color: "Prateado" },
  "Apple iPhone 17 Pro Max": { storage: "1024", color: "Prateado" },
  "Samsung Galaxy S26": { storage: "256", color: "Dourado" },
  "Samsung Galaxy S26+": { storage: "512", color: "Violeta" },
  "Samsung Galaxy S26 Ultra": { storage: "1024", color: "Preto" },
};

function Icon({ name }: { name: IconName }) {
  const paths = {
    arrow: <path d="m7 17 10-10M8 7h9v9" />,
    bolt: <path d="M13 2 4.8 13H11l-1 9 8.2-11H12l1-9Z" />,
    check: <path d="m5 12 4 4L19 6" />,
    database: (
      <>
        <ellipse cx="12" cy="5" rx="8" ry="3" />
        <path d="M4 5v7c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12v7c0 1.7 3.6 3 8 3s8-1.3 8-3v-7" />
      </>
    ),
    signal: <path d="M4 18v2M8 14v6M12 10v10M16 6v14M20 2v18" />,
    grid: (
      <>
        <rect x="3" y="3" width="7" height="7" />
        <rect x="14" y="3" width="7" height="7" />
        <rect x="3" y="14" width="7" height="7" />
        <rect x="14" y="14" width="7" height="7" />
      </>
    ),
    search: (
      <>
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-4-4" />
      </>
    ),
    plus: <path d="M12 5v14M5 12h14" />,
  };
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      {paths[name]}
    </svg>
  );
}

function variantLabel(variant: Variant): string {
  const storage = variant.attributes.storage_gb;
  const color = variant.attributes.color;
  return [
    storage
      ? `${Number(storage) >= 1024 ? `${Number(storage) / 1024} TB` : `${storage} GB`}`
      : null,
    color,
  ]
    .filter(Boolean)
    .join(" · ");
}

function runLabel(run: CollectionRun | undefined): string {
  if (!run) return "Pronta";
  return {
    pending: "Na fila",
    running: "Coletando",
    succeeded: "Atualizada",
    failed: "Falhou",
    partial: "Parcial",
  }[run.status];
}

function sourceState(source: Source): { label: string; tone: string } {
  if (source.status === "enabled") return { label: "Integrada", tone: "ready" };
  if (["iplace", "magalu"].includes(source.adapter_name))
    return { label: "Acesso direto bloqueado", tone: "blocked" };
  if (source.adapter_name === "catalog_reference")
    return { label: "Referência oficial", tone: "reference" };
  if (source.adapter_name.endsWith("_api")) return { label: "API oficial pendente", tone: "api" };
  return { label: "Em qualificação", tone: "candidate" };
}

const browserFallbackAdapters = new Set(["amazon", "americanas", "carrefour"]);

function enabledSourceDescription(source: Source): string {
  if (browserFallbackAdapters.has(source.adapter_name)) {
    return "HTTP estruturado primeiro; Chromium headless somente se JSON-LD e DOM forem insuficientes.";
  }
  return "Coleta HTTP com JSON-LD prioritário, adapter dedicado e controles de rede.";
}

function sourceAppliesToProduct(source: Source, product: Product | null): boolean {
  if (!product) return false;
  if (source.adapter_name === "zoom") return source.name === `Zoom — ${product.name}`;
  if (source.adapter_name === "two_a_finder") return source.name === `2aFinder — ${product.name}`;
  if (source.adapter_name === "buscape") return source.name === `Buscapé — ${product.name}`;
  if (source.adapter_name === "samsung_shop")
    return source.name === `Samsung Shop — ${product.name.replace("Samsung ", "")}`;
  if (source.adapter_name === "iplace") return product.name === "Apple iPhone 17";
  if (["amazon", "americanas", "carrefour"].includes(source.adapter_name))
    return product.name === "Apple iPhone 17";
  if (source.adapter_name === "fast_shop")
    return source.name === "Fast Shop"
      ? product.name === "Apple iPhone 17"
      : source.name === `Fast Shop — ${product.name}`;
  if (source.adapter_name === "kabum") return source.name === `KaBuM! — ${product.name}`;
  return true;
}

function sourceDisplayRank(source: Source): number {
  const ranks: Record<string, number> = {
    amazon: 0,
    americanas: 1,
    carrefour: 2,
    iplace: 3,
    magalu: 4,
  };
  return ranks[source.adapter_name] ?? 10;
}

function LandingPage({ onEnter }: { onEnter: () => void }) {
  return (
    <div className="landing-shell">
      <header className="topbar">
        <a className="brand" href="#top">
          <span className="brand-mark">
            <Icon name="signal" />
          </span>
          <span>Signal Price</span>
        </a>
        <button className="text-action" type="button" onClick={onEnter}>
          Entrar na plataforma <Icon name="arrow" />
        </button>
      </header>
      <main id="top">
        <section className="hero landing-hero">
          <div className="hero-copy">
            <p className="eyebrow">Inteligência de mercado · Evidência real</p>
            <h1>
              O mercado muda.
              <br />
              <em>Você enxerga primeiro.</em>
            </h1>
            <p className="hero-description">
              Uma plataforma de pricing que transforma sinais dispersos da internet em evidência
              comparável, rastreável e pronta para decisão.
            </p>
          </div>
          <button className="primary-action" type="button" onClick={onEnter}>
            <span>Explorar inteligência</span>
            <Icon name="arrow" />
          </button>
        </section>
        <section className="landing-proof" aria-label="Capacidades da plataforma">
          <article>
            <span>01</span>
            <strong>Descoberta ampla</strong>
            <p>Radar multiconsulta com diversidade de domínios e qualificação de fontes.</p>
          </article>
          <article>
            <span>02</span>
            <strong>Coleta rastreável</strong>
            <p>Spiders isolados, evidência versionada e histórico temporal por oferta.</p>
          </article>
          <article>
            <span>03</span>
            <strong>Comparação defensável</strong>
            <p>Variante, condição e base comercial explícitas antes de qualquer indicador.</p>
          </article>
        </section>
        <section className="landing-cta">
          <p className="eyebrow">Do sinal à decisão</p>
          <h2>
            Mais amplitude.
            <br />
            Menos ruído.
          </h2>
          <button className="secondary-action" type="button" onClick={onEnter}>
            Ir para o workspace <Icon name="arrow" />
          </button>
        </section>
      </main>
      <footer>
        <span>Signal Price · Inteligência de preços</span>
        <span>Python · Scrapy · FastAPI · PostgreSQL · React</span>
      </footer>
    </div>
  );
}

function PriceRange({ comparison }: { comparison: Comparison }) {
  const min = Number(comparison.min_price ?? 0);
  const median = Number(comparison.median_price ?? 0);
  const max = Number(comparison.max_price ?? 0);
  const position = max === min ? 50 : ((median - min) / (max - min)) * 100;
  return (
    <section className="price-range" aria-label="Faixa de preços comparáveis">
      <div className="range-heading">
        <div>
          <p className="eyebrow">Distribuição observada</p>
          <h2>Onde o mercado está agora</h2>
        </div>
        <span className="sample-badge">{comparison.included_offer_count} ofertas válidas</span>
      </div>
      <div className="range-visual">
        <div className="range-median-label">
          <span>Mediana</span>
          <strong>{formatMoney(comparison.median_price)}</strong>
        </div>
        <svg
          aria-hidden="true"
          className="range-graph"
          preserveAspectRatio="none"
          viewBox="0 0 100 64"
        >
          <defs>
            <linearGradient id="range-gradient" x1="0" x2="1">
              <stop offset="0" stopColor="#718d1f" />
              <stop offset="0.55" stopColor="#b6dc3b" />
              <stop offset="1" stopColor="#ff745c" />
            </linearGradient>
          </defs>
          <line className="range-track" x1="0" x2="100" y1="42" y2="42" />
          <line className="range-boundary" x1="0.5" x2="0.5" y1="34" y2="50" />
          <line className="range-boundary" x1="99.5" x2="99.5" y1="34" y2="50" />
          <line className="range-marker" x1={position} x2={position} y1="24" y2="54" />
          <circle className="range-marker-dot" cx={position} cy="42" r="2.2" />
        </svg>
      </div>
      <div className="range-limits">
        <div>
          <span>Mínimo</span>
          <strong>{formatMoney(comparison.min_price)}</strong>
        </div>
        <div className="range-limit-right">
          <span>Máximo</span>
          <strong>{formatMoney(comparison.max_price)}</strong>
        </div>
      </div>
    </section>
  );
}

type DiscoveryProps = {
  candidates: SourceCandidate[];
  query: string;
  busy: boolean;
  setQuery: (value: string) => void;
  onSearch: () => Promise<void>;
};

function DiscoveryPanel({ candidates, query, busy, setQuery, onSearch }: DiscoveryProps) {
  const domains = new Set(candidates.map((item) => item.domain)).size;
  return (
    <section className="discovery-panel" aria-labelledby="discovery-title">
      <div className="discovery-heading">
        <div>
          <p className="eyebrow">Radar aberto</p>
          <h2 id="discovery-title">Descoberta ampla na internet</h2>
          <p>
            Múltiplas consultas, no máximo três resultados por domínio e prioridade para fontes
            reconhecidas. Resultados entram como candidatos, nunca como verdade automática.
          </p>
        </div>
        <form
          className="discovery-form"
          onSubmit={(event) => {
            event.preventDefault();
            void onSearch();
          }}
        >
          <label htmlFor="discovery-query">Produto ou referência</label>
          <div>
            <input
              id="discovery-query"
              value={query}
              minLength={3}
              maxLength={160}
              onChange={(event) => setQuery(event.target.value)}
            />
            <button type="submit" disabled={busy || query.trim().length < 3}>
              {busy ? "Varrendo…" : "Varrer a web"}
            </button>
          </div>
        </form>
      </div>
      <div className="radar-stats">
        <span>
          <strong>{candidates.length}</strong> referências
        </span>
        <span>
          <strong>{domains}</strong> domínios
        </span>
        <span>
          <strong>{candidates.filter((item) => item.trust_tier === "trusted").length}</strong>{" "}
          prioritárias
        </span>
      </div>
      <div className="candidate-grid">
        {candidates.slice(0, 24).map((candidate) => (
          <a
            className="candidate-card"
            key={candidate.id}
            href={candidate.url}
            target="_blank"
            rel="noreferrer noopener"
          >
            <span className={`trust-badge trust-${candidate.trust_tier}`}>
              {candidate.trust_tier === "trusted"
                ? "Fonte prioritária"
                : candidate.trust_tier === "known"
                  ? "Fonte conhecida"
                  : "Requer revisão"}
            </span>
            <strong>{candidate.title}</strong>
            <p>{candidate.snippet}</p>
            <small>{candidate.domain}</small>
          </a>
        ))}
        {candidates.length === 0 ? (
          <p className="candidate-empty">
            Configure a chave do provedor no backend e execute uma busca para montar o radar.
          </p>
        ) : null}
      </div>
    </section>
  );
}

function AppSkeleton() {
  return (
    <main className="loading-shell" aria-label="Carregando painel">
      <div className="loading-mark" />
      <p>Organizando inteligência de mercado…</p>
    </main>
  );
}

export function App() {
  const [inPlatform, setInPlatform] = useState(() =>
    window.location.pathname.startsWith("/platform"),
  );
  const [activeView, setActiveView] = useState<View>("overview");
  const [sources, setSources] = useState<Source[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [variants, setVariants] = useState<Variant[]>([]);
  const [variantCounts, setVariantCounts] = useState<Record<string, number>>({});
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null);
  const [selectedVariantId, setSelectedVariantId] = useState<string | null>(null);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [intelligence, setIntelligence] = useState<ProductIntelligence | null>(null);
  const [runsBySource, setRunsBySource] = useState<Record<string, CollectionRun>>({});
  const [busySourceIds, setBusySourceIds] = useState<string[]>([]);
  const [candidates, setCandidates] = useState<SourceCandidate[]>([]);
  const [discoveryQuery, setDiscoveryQuery] = useState("iPhone 17 preço comprar Brasil");
  const [discoveryBusy, setDiscoveryBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDeviceForm, setShowDeviceForm] = useState(false);
  const [showSourceForm, setShowSourceForm] = useState(false);
  const [deviceForm, setDeviceForm] = useState({
    name: "",
    brand: "",
    storages: "256, 512",
    colors: "Preto, Branco",
  });
  const [sourceForm, setSourceForm] = useState({ title: "", url: "" });

  const selectedProduct = products.find((item) => item.id === selectedProductId) ?? null;
  const selectedVariant = variants.find((item) => item.id === selectedVariantId) ?? null;
  const visibleProducts = useMemo(
    () => products.filter((item) => item.brand !== "Nimbus"),
    [products],
  );
  const realSources = sources.filter((item) => item.kind === "real" && item.status === "enabled");
  const productSources = realSources
    .filter((source) => sourceAppliesToProduct(source, selectedProduct))
    .sort((left, right) => sourceDisplayRank(left) - sourceDisplayRank(right));
  const hasProductSources = productSources.length > 0;
  const registrySources = sources
    .filter((item) => item.kind === "real" && item.status !== "disabled")
    .sort((left, right) => sourceDisplayRank(left) - sourceDisplayRank(right));
  const collectionBusy = busySourceIds.length > 0;

  const enterPlatform = () => {
    window.history.pushState({}, "", "/platform");
    setInPlatform(true);
  };
  const leavePlatform = () => {
    window.history.pushState({}, "", "/");
    setInPlatform(false);
  };

  const loadComparison = useCallback(async (variantId: string) => {
    setComparison(await api.getComparison(variantId));
  }, []);

  const loadIntelligence = useCallback(async (productId: string) => {
    setIntelligence(await api.getProductIntelligence(productId));
  }, []);

  const reloadCatalog = useCallback(async () => {
    const productList = await api.listProducts();
    setProducts(productList);
    setSelectedProductId(
      (current) => current ?? productList.find((item) => item.brand !== "Nimbus")?.id ?? null,
    );
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([api.listSources(false), api.listProducts(), api.listCandidates()])
      .then(([sourceList, productList, candidateList]) => {
        if (!active) return;
        setSources(sourceList);
        setProducts(productList);
        setCandidates(candidateList);
        setSelectedProductId(productList.find((item) => item.brand !== "Nimbus")?.id ?? null);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Falha ao carregar dados");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (products.length === 0) return;
    let active = true;
    Promise.all(
      products.map(
        async (product) => [product.id, (await api.listVariants(product.id)).length] as const,
      ),
    )
      .then((items) => {
        if (active) setVariantCounts(Object.fromEntries(items));
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [products]);

  useEffect(() => {
    if (!selectedProductId) return;
    let active = true;
    setIntelligence(null);
    Promise.all([
      api.listVariants(selectedProductId),
      api.getProductIntelligence(selectedProductId),
    ])
      .then(([items, productIntelligence]) => {
        if (!active) return;
        setVariants(items);
        setIntelligence(productIntelligence);
        const product = products.find((item) => item.id === selectedProductId);
        const priority = product ? priorityVariantByProduct[product.name] : undefined;
        const defaultVariant =
          (priority
            ? items.find(
                (item) =>
                  item.attributes.storage_gb === priority.storage &&
                  item.attributes.color === priority.color,
              )
            : undefined) ??
          items.find(
            (item) => item.attributes.storage_gb === "256" && item.attributes.color === "Preto",
          ) ??
          items.find((item) => item.attributes.storage_gb === "256") ??
          items[0];
        setSelectedVariantId(defaultVariant?.id ?? null);
        setComparison(null);
      })
      .catch((reason: unknown) => {
        if (active)
          setError(reason instanceof Error ? reason.message : "Falha ao carregar variantes");
      });
    return () => {
      active = false;
    };
  }, [products, selectedProductId]);

  useEffect(() => {
    if (!selectedVariantId) return;
    loadComparison(selectedVariantId).catch((reason: unknown) =>
      setError(reason instanceof Error ? reason.message : "Falha ao comparar ofertas"),
    );
  }, [loadComparison, selectedVariantId]);

  const pollRun = useCallback(async (initialRun: CollectionRun) => {
    let current = initialRun;
    for (let attempt = 0; attempt < 90 && !terminalStatuses.has(current.status); attempt += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 1000));
      current = await api.getRun(initialRun.id);
      setRunsBySource((existing) => ({ ...existing, [current.source_id]: current }));
    }
    return current;
  }, []);

  const collectSource = useCallback(
    async (sourceId: string) => {
      setError(null);
      setBusySourceIds((current) => [...current, sourceId]);
      try {
        const run = await api.collectSource(sourceId);
        setRunsBySource((existing) => ({ ...existing, [sourceId]: run }));
        const finalRun = await pollRun(run);
        if (!terminalStatuses.has(finalRun.status))
          throw new Error("A coleta excedeu o tempo de acompanhamento");
        if (finalRun.status === "failed")
          throw new Error(finalRun.failure_reason ?? "A coleta falhou");
      } finally {
        setBusySourceIds((current) => current.filter((id) => id !== sourceId));
      }
    },
    [pollRun],
  );

  const collectAll = async () => {
    if (!hasProductSources) {
      setError(
        "Este equipamento ainda não possui coletor homologado. Use o Radar web para qualificar novas fontes.",
      );
      return;
    }
    try {
      await Promise.all(productSources.map((source) => collectSource(source.id)));
      if (selectedVariantId) await loadComparison(selectedVariantId);
      if (selectedProductId) await loadIntelligence(selectedProductId);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Falha ao atualizar mercado");
    }
  };

  const runDiscovery = async () => {
    setDiscoveryBusy(true);
    setError(null);
    try {
      setCandidates(await api.discover(discoveryQuery.trim()));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Falha na busca ampla");
    } finally {
      setDiscoveryBusy(false);
    }
  };

  const createDevice = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    const storages = deviceForm.storages
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    const colors = deviceForm.colors
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    const model = deviceForm.name
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_|_$/g, "");
    try {
      const detail = await api.createProduct({
        name: deviceForm.name,
        brand: deviceForm.brand,
        category: "smartphone",
        variants: storages.flatMap((storage) =>
          colors.map((color) => ({
            attributes: {
              brand: deviceForm.brand.toLowerCase(),
              model,
              region: "br",
              storage_gb: storage,
              color,
            },
            gtin: null,
          })),
        ),
      });
      setShowDeviceForm(false);
      setDeviceForm({ name: "", brand: "", storages: "256, 512", colors: "Preto, Branco" });
      await reloadCatalog();
      setSelectedProductId(detail.product.id);
      setVariants(detail.variants);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Falha ao cadastrar equipamento");
    }
  };

  const createSourceCandidate = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      const candidate = await api.createCandidate({ title: sourceForm.title, url: sourceForm.url });
      setCandidates((current) => [
        candidate,
        ...current.filter((item) => item.id !== candidate.id),
      ]);
      setShowSourceForm(false);
      setSourceForm({ title: "", url: "" });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Falha ao cadastrar fonte");
    }
  };

  const groups = useMemo(
    () => ({
      Apple: visibleProducts.filter((item) => item.brand === "Apple"),
      Samsung: visibleProducts.filter((item) => item.brand === "Samsung"),
      Motorola: visibleProducts.filter((item) => item.brand === "Motorola"),
      Outros: visibleProducts.filter(
        (item) => !["Apple", "Samsung", "Motorola"].includes(item.brand),
      ),
    }),
    [visibleProducts],
  );

  if (!inPlatform) return <LandingPage onEnter={enterPlatform} />;
  if (loading) return <AppSkeleton />;

  const nav: Array<{ id: View; label: string; icon: IconName }> = [
    { id: "overview", label: "Visão de mercado", icon: "signal" },
    { id: "catalog", label: "Equipamentos", icon: "grid" },
    { id: "sources", label: "Fontes", icon: "database" },
    { id: "discovery", label: "Radar web", icon: "search" },
  ];

  return (
    <div className="platform-shell">
      <aside className="platform-sidebar">
        <button className="brand brand-button" type="button" onClick={leavePlatform}>
          <span className="brand-mark">
            <Icon name="signal" />
          </span>
          <span>Signal Price</span>
        </button>
        <nav>
          {nav.map((item) => (
            <button
              key={item.id}
              type="button"
              className={activeView === item.id ? "nav-item active" : "nav-item"}
              onClick={() => setActiveView(item.id)}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-status">
          <span className="pulse-dot" />
          <div>
            <strong>Operação local</strong>
            <small>{realSources.length} fontes integradas</small>
          </div>
          <p className="privacy-note">
            A consulta é enviada ao provedor Brave Search. Não inclua dados pessoais ou
            confidenciais; o sistema persiste apenas uma identificação genérica da busca.
          </p>
        </div>
      </aside>

      <div className="platform-content">
        <header className="platform-topbar">
          <div>
            <p className="eyebrow">Workspace de inteligência</p>
            <strong>
              {activeView === "overview"
                ? "Mercado"
                : nav.find((item) => item.id === activeView)?.label}
            </strong>
          </div>
          <div className="topbar-actions">
            <button type="button" className="ghost-action" onClick={leavePlatform}>
              Ver apresentação
            </button>
            <button
              type="button"
              className="primary-compact"
              onClick={() =>
                activeView === "catalog"
                  ? setShowDeviceForm(true)
                  : activeView === "sources"
                    ? setShowSourceForm(true)
                    : setActiveView("discovery")
              }
            >
              <Icon name="plus" />{" "}
              {activeView === "catalog"
                ? "Novo equipamento"
                : activeView === "sources"
                  ? "Adicionar fonte"
                  : "Nova busca"}
            </button>
          </div>
        </header>

        {error ? (
          <div className="error-banner" role="alert">
            <strong>Não foi possível concluir a operação.</strong>
            <span>{error}</span>
            <button type="button" onClick={() => setError(null)}>
              Fechar
            </button>
          </div>
        ) : null}

        <main className="platform-main">
          {activeView === "overview" ? (
            <>
              <section className="workspace-intro">
                <div>
                  <p className="eyebrow">Pulso do mercado</p>
                  <h1>
                    Inteligência que explica
                    <br />
                    cada número.
                  </h1>
                </div>
                <div className="device-picker">
                  <label htmlFor="product-select">Equipamento monitorado</label>
                  <select
                    id="product-select"
                    value={selectedProductId ?? ""}
                    onChange={(event) => setSelectedProductId(event.target.value)}
                  >
                    {visibleProducts.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                  <button
                    className="primary-action"
                    type="button"
                    onClick={collectAll}
                    disabled={collectionBusy || !hasProductSources}
                  >
                    <span>
                      {collectionBusy
                        ? "Coletando mercado"
                        : hasProductSources
                          ? "Atualizar mercado"
                          : "Sem coletor ativo"}
                    </span>
                    <Icon name={collectionBusy ? "bolt" : "arrow"} />
                  </button>
                </div>
              </section>
              <ProductIntelligencePanel product={selectedProduct} intelligence={intelligence} />
              <section className="metrics-grid" aria-label="Resumo da comparação">
                <article className="metric-card metric-card-featured">
                  <span className="metric-index">01</span>
                  <p>Mediana do mercado</p>
                  <strong>{formatMoney(comparison?.median_price ?? null)}</strong>
                  <small>
                    {selectedVariant ? variantLabel(selectedVariant) : "Selecione uma variante"}
                  </small>
                </article>
                <article className="metric-card">
                  <span className="metric-index">02</span>
                  <p>Ofertas comparáveis</p>
                  <strong>{comparison?.included_offer_count ?? 0}</strong>
                  <small>{comparison?.excluded.length ?? 0} exclusões explicadas</small>
                </article>
                <article className="metric-card">
                  <span className="metric-index">03</span>
                  <p>Varejistas distintos</p>
                  <strong>{comparison?.retailer_count ?? 0}</strong>
                  <small>
                    piso operacional 6–8 · {comparison?.source_count ?? 0} canais de evidência
                  </small>
                </article>
                <article className="metric-card">
                  <span className="metric-index">04</span>
                  <p>Referência</p>
                  <strong className="metric-date">
                    {formatDate(comparison?.newest_observation_at ?? null)}
                  </strong>
                  <small>evidência direta da fonte</small>
                </article>
              </section>
              <div className="workspace-grid">
                <aside className="control-panel">
                  <div className="panel-heading">
                    <div>
                      <p className="eyebrow">Coletores</p>
                      <h2>Fontes ativas</h2>
                    </div>
                    <Icon name="database" />
                  </div>
                  <div className="source-list">
                    {productSources.map((source, index) => {
                      const run = runsBySource[source.id];
                      const busy = busySourceIds.includes(source.id);
                      return (
                        <article className="source-item" key={source.id}>
                          <div className="source-number">0{index + 1}</div>
                          <div className="source-copy">
                            <strong>{source.name}</strong>
                            <span>
                              <i className={`status-dot status-${run?.status ?? "idle"}`} />
                              {runLabel(run)}
                            </span>
                          </div>
                          <button
                            className="icon-action"
                            type="button"
                            onClick={() => {
                              collectSource(source.id)
                                .then(() =>
                                  Promise.all([
                                    selectedVariantId
                                      ? loadComparison(selectedVariantId)
                                      : Promise.resolve(),
                                    selectedProductId
                                      ? loadIntelligence(selectedProductId)
                                      : Promise.resolve(),
                                  ]),
                                )
                                .catch((reason: unknown) =>
                                  setError(
                                    reason instanceof Error ? reason.message : "Falha na coleta",
                                  ),
                                );
                            }}
                            disabled={busy}
                            aria-label={`Coletar ${source.name}`}
                          >
                            <Icon name={busy ? "bolt" : "arrow"} />
                          </button>
                        </article>
                      );
                    })}
                    {!hasProductSources ? (
                      <div className="source-empty">
                        <strong>Catálogo pronto, coleta em qualificação.</strong>
                        <span>
                          Este modelo está cadastrado com suas variantes oficiais, mas ainda não
                          possui adapter habilitado.
                        </span>
                        <button type="button" onClick={() => setActiveView("discovery")}>
                          Encontrar fontes
                        </button>
                      </div>
                    ) : null}
                  </div>
                  <p className="lab-note">
                    Spiders dedicados, robots.txt, throttling, allowlist de destino e evidência
                    versionada.
                  </p>
                </aside>
                <section className="insights-panel">
                  <div className="catalog-heading">
                    <div>
                      <p className="eyebrow">Catálogo canônico</p>
                      <h2>{selectedProduct?.name ?? "Nenhum produto"}</h2>
                    </div>
                    <span className="synthetic-label">
                      {selectedProduct?.brand ?? "—"} · Brasil
                    </span>
                  </div>
                  <ul className="variant-tabs" aria-label="Variantes do produto">
                    {variants.map((variant) => (
                      <li key={variant.id}>
                        <button
                          type="button"
                          className={
                            variant.id === selectedVariantId ? "variant-tab active" : "variant-tab"
                          }
                          onClick={() => setSelectedVariantId(variant.id)}
                        >
                          {variantLabel(variant)}
                        </button>
                      </li>
                    ))}
                  </ul>
                  {comparison?.has_comparable_data ? (
                    <>
                      <PriceRange comparison={comparison} />
                      <section className="offer-section">
                        <div className="section-title-row">
                          <h3>Ofertas que sustentam a análise</h3>
                          <span>Atual mais recente por anúncio</span>
                        </div>
                        <div className="offer-list">
                          {comparison.offers.map((offer) => (
                            <a
                              className="offer-row"
                              key={offer.offer_id}
                              href={offer.url}
                              target="_blank"
                              rel="noreferrer noopener"
                            >
                              <div className="offer-identity">
                                <span className="offer-check">
                                  <Icon name="check" />
                                </span>
                                <div>
                                  <strong>{offer.seller_name}</strong>
                                  <span>{offer.source_name}</span>
                                </div>
                              </div>
                              <div className="offer-tags">
                                <span>
                                  {offer.payment_terms.price_basis === "cash"
                                    ? "À vista"
                                    : "Preço anunciado"}
                                </span>
                                {offer.payment_terms.condition_summary ? (
                                  <span>{offer.payment_terms.condition_summary}</span>
                                ) : null}
                                {offer.payment_terms.installment_count ? (
                                  <span>{offer.payment_terms.installment_count}x</span>
                                ) : null}
                                <span>
                                  {offer.shipping.known ? "Frete informado" : "Frete desconhecido"}
                                </span>
                              </div>
                              <strong className="offer-price">{formatMoney(offer.price)}</strong>
                            </a>
                          ))}
                        </div>
                      </section>
                      {comparison.excluded.length > 0 ? (
                        <details className="excluded-panel">
                          <summary>
                            {comparison.excluded.length} ofertas fora da população comparável
                          </summary>
                          <div>
                            {comparison.excluded.map((offer) => (
                              <p key={offer.offer_id}>
                                <strong>{offer.seller_name}</strong>
                                <span>{offer.reason}</span>
                              </p>
                            ))}
                          </div>
                        </details>
                      ) : null}
                    </>
                  ) : (
                    <section className="empty-state">
                      <span className="empty-symbol">
                        <Icon name="signal" />
                      </span>
                      <p className="eyebrow">Aguardando evidência</p>
                      <h2>Ainda sem amostra comparável.</h2>
                      <p>
                        {hasProductSources
                          ? "Execute a coleta ou abra o Radar para descobrir novas referências para este equipamento."
                          : "Abra o Radar para descobrir e qualificar referências para este equipamento."}
                      </p>
                      <div className="empty-actions">
                        <button
                          type="button"
                          className="secondary-action"
                          onClick={collectAll}
                          disabled={collectionBusy || !hasProductSources}
                        >
                          {hasProductSources ? "Coletar fontes" : "Sem coletor ativo"}{" "}
                          <Icon name="arrow" />
                        </button>
                        <button
                          type="button"
                          className="ghost-action"
                          onClick={() => {
                            setDiscoveryQuery(
                              `${selectedProduct?.name ?? "smartphone"} preço Brasil`,
                            );
                            setActiveView("discovery");
                          }}
                        >
                          Abrir radar
                        </button>
                      </div>
                    </section>
                  )}
                </section>
              </div>
            </>
          ) : null}

          {activeView === "catalog" ? (
            <section className="management-view">
              <div className="view-heading">
                <div>
                  <p className="eyebrow">Portfólio monitorado</p>
                  <h1>Equipamentos</h1>
                  <p>
                    Famílias canônicas e suas variantes. O catálogo não nasce de texto não
                    confiável: cada item é cadastrado e revisável.
                  </p>
                </div>
                <button
                  className="primary-action"
                  type="button"
                  onClick={() => setShowDeviceForm((current) => !current)}
                >
                  <span>Novo equipamento</span>
                  <Icon name="plus" />
                </button>
              </div>
              {showDeviceForm ? (
                <form className="creation-panel" onSubmit={createDevice}>
                  <div>
                    <p className="eyebrow">Cadastro guiado</p>
                    <h2>Adicionar ao monitoramento</h2>
                  </div>
                  <label>
                    Fabricante
                    <input
                      required
                      value={deviceForm.brand}
                      onChange={(event) =>
                        setDeviceForm({ ...deviceForm, brand: event.target.value })
                      }
                      placeholder="Ex.: Motorola"
                    />
                  </label>
                  <label>
                    Nome do modelo
                    <input
                      required
                      value={deviceForm.name}
                      onChange={(event) =>
                        setDeviceForm({ ...deviceForm, name: event.target.value })
                      }
                      placeholder="Ex.: Motorola Edge 70"
                    />
                  </label>
                  <label>
                    Armazenamentos em GB
                    <input
                      required
                      value={deviceForm.storages}
                      onChange={(event) =>
                        setDeviceForm({ ...deviceForm, storages: event.target.value })
                      }
                    />
                  </label>
                  <label>
                    Cores
                    <input
                      required
                      value={deviceForm.colors}
                      onChange={(event) =>
                        setDeviceForm({ ...deviceForm, colors: event.target.value })
                      }
                    />
                  </label>
                  <button type="submit">Criar equipamento e variantes</button>
                </form>
              ) : null}
              {Object.entries(groups).map(([brand, items]) =>
                items.length > 0 ? (
                  <div className="catalog-group" key={brand}>
                    <div className="group-title">
                      <h2>{brand}</h2>
                      <span>{items.length} modelos</span>
                    </div>
                    <div className="product-grid">
                      {items.map((product) => (
                        <button
                          type="button"
                          key={product.id}
                          className="product-card"
                          onClick={() => {
                            setSelectedProductId(product.id);
                            setActiveView("overview");
                          }}
                        >
                          <span className="product-monogram">{product.brand.slice(0, 1)}</span>
                          <small>{product.category}</small>
                          <strong>{product.name.replace(`${product.brand} `, "")}</strong>
                          <div>
                            <span>{variantCounts[product.id] ?? "—"} variantes</span>
                            <Icon name="arrow" />
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                ) : null,
              )}
            </section>
          ) : null}

          {activeView === "sources" ? (
            <section className="management-view">
              <div className="view-heading">
                <div>
                  <p className="eyebrow">Qualidade e cobertura</p>
                  <h1>Fontes</h1>
                  <p>
                    Conectores de API comercial são opcionais e ainda não estão credenciados; hoje a
                    coleta homologada usa JSON-LD, DOM e browser headless como último recurso.
                  </p>
                </div>
                <button
                  className="primary-action"
                  type="button"
                  onClick={() => setShowSourceForm((current) => !current)}
                >
                  <span>Adicionar fonte</span>
                  <Icon name="plus" />
                </button>
              </div>
              {showSourceForm ? (
                <form className="creation-panel source-creation" onSubmit={createSourceCandidate}>
                  <div>
                    <p className="eyebrow">Onboarding governado</p>
                    <h2>Nova fonte candidata</h2>
                    <p>
                      A URL será registrada para avaliação. Nenhum coletor é habilitado
                      automaticamente.
                    </p>
                  </div>
                  <label>
                    Nome da fonte
                    <input
                      required
                      value={sourceForm.title}
                      onChange={(event) =>
                        setSourceForm({ ...sourceForm, title: event.target.value })
                      }
                      placeholder="Ex.: Loja oficial Motorola"
                    />
                  </label>
                  <label>
                    URL pública
                    <input
                      required
                      type="url"
                      value={sourceForm.url}
                      onChange={(event) =>
                        setSourceForm({ ...sourceForm, url: event.target.value })
                      }
                      placeholder="https://..."
                    />
                  </label>
                  <button type="submit">Enviar para qualificação</button>
                </form>
              ) : null}
              <div className="source-registry">
                {registrySources.map((source) => {
                  const state = sourceState(source);
                  return (
                    <article className="registry-card" key={source.id}>
                      <div>
                        <span className={`source-state state-${state.tone}`}>{state.label}</span>
                        <small>{new URL(source.base_url).hostname}</small>
                      </div>
                      <strong>{source.name}</strong>
                      <p>
                        {source.adapter_name === "catalog_reference"
                          ? "Sustenta catálogo, especificações e identidade do produto."
                          : source.status === "enabled"
                            ? enabledSourceDescription(source)
                            : ["iplace", "magalu"].includes(source.adapter_name)
                              ? "URL real qualificada, mas o acesso direto do coletor recebe HTTP 403. Sem contorno de bloqueio."
                              : source.adapter_name.endsWith("_api")
                                ? "Canal oficial mapeado; requer credenciais e homologação."
                                : "Domínio reconhecido aguardando avaliação de acesso e adapter."}
                      </p>
                      <a href={source.base_url} target="_blank" rel="noreferrer noopener">
                        Abrir fonte <Icon name="arrow" />
                      </a>
                    </article>
                  );
                })}
              </div>
            </section>
          ) : null}

          {activeView === "discovery" ? (
            <DiscoveryPanel
              candidates={candidates}
              query={discoveryQuery}
              busy={discoveryBusy}
              setQuery={setDiscoveryQuery}
              onSearch={runDiscovery}
            />
          ) : null}
        </main>
        <footer>
          <span>Signal Price · Workspace local</span>
          <span>Dados reais, candidatos e laboratório em camadas distintas.</span>
        </footer>
      </div>
      <div className="sr-only" aria-live="polite">
        {collectionBusy ? "Coleta em andamento" : (error ?? "Painel atualizado")}
      </div>
    </div>
  );
}
