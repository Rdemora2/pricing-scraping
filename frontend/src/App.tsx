import { useCallback, useEffect, useState } from "react";

import { api } from "./api";
import type { CollectionRun, Comparison, Product, Source, Variant } from "./types";

const terminalStatuses = new Set<CollectionRun["status"]>(["succeeded", "failed", "partial"]);

const currencyFormatter = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  minimumFractionDigits: 2,
});

const dateFormatter = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

function formatMoney(value: string | null): string {
  return value === null ? "—" : currencyFormatter.format(Number(value));
}

function formatDate(value: string | null): string {
  return value === null ? "Sem coleta" : dateFormatter.format(new Date(value));
}

function variantLabel(variant: Variant): string {
  const storage = variant.attributes.storage_gb;
  const color = variant.attributes.color;
  return [storage ? `${storage} GB` : null, color].filter(Boolean).join(" · ");
}

function runLabel(run: CollectionRun | undefined): string {
  if (!run) return "Pronta";
  const labels: Record<CollectionRun["status"], string> = {
    pending: "Na fila",
    running: "Coletando",
    succeeded: "Atualizada",
    failed: "Falhou",
    partial: "Parcial",
  };
  return labels[run.status];
}

function Icon({ name }: { name: "arrow" | "bolt" | "check" | "database" | "signal" }) {
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
  };

  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      {paths[name]}
    </svg>
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

function AppSkeleton() {
  return (
    <main className="loading-shell" aria-label="Carregando painel">
      <div className="loading-mark" />
      <p>Sincronizando sinais do laboratório…</p>
    </main>
  );
}

export function App() {
  const [sources, setSources] = useState<Source[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [variants, setVariants] = useState<Variant[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null);
  const [selectedVariantId, setSelectedVariantId] = useState<string | null>(null);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [runsBySource, setRunsBySource] = useState<Record<string, CollectionRun>>({});
  const [busySourceIds, setBusySourceIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const selectedProduct = products.find((product) => product.id === selectedProductId) ?? null;
  const selectedVariant = variants.find((variant) => variant.id === selectedVariantId) ?? null;

  const loadComparison = useCallback(async (variantId: string) => {
    const result = await api.getComparison(variantId);
    setComparison(result);
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([api.listSources(), api.listProducts()])
      .then(([sourceList, productList]) => {
        if (!active) return;
        setSources(sourceList);
        setProducts(productList);
        setSelectedProductId(productList[0]?.id ?? null);
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
    if (!selectedProductId) return;
    let active = true;
    api
      .listVariants(selectedProductId)
      .then((variantList) => {
        if (!active) return;
        setVariants(variantList);
        setSelectedVariantId(variantList[0]?.id ?? null);
      })
      .catch((reason: unknown) => {
        if (active)
          setError(reason instanceof Error ? reason.message : "Falha ao carregar variantes");
      });
    return () => {
      active = false;
    };
  }, [selectedProductId]);

  useEffect(() => {
    if (!selectedVariantId) return;
    loadComparison(selectedVariantId).catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : "Falha ao comparar ofertas");
    });
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
        if (!terminalStatuses.has(finalRun.status)) {
          throw new Error("A coleta excedeu o tempo de acompanhamento");
        }
        if (finalRun.status === "failed") {
          throw new Error(finalRun.failure_reason ?? "A coleta falhou");
        }
      } finally {
        setBusySourceIds((current) => current.filter((id) => id !== sourceId));
      }
    },
    [pollRun],
  );

  const collectAll = async () => {
    try {
      await Promise.all(sources.map((source) => collectSource(source.id)));
      if (selectedVariantId) await loadComparison(selectedVariantId);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Falha ao atualizar o laboratório");
    }
  };

  const collectionBusy = busySourceIds.length > 0;
  const successfulSources = Object.values(runsBySource).filter(
    (run) => run.status === "succeeded",
  ).length;

  if (loading) return <AppSkeleton />;

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Signal Price, início">
          <span className="brand-mark">
            <Icon name="signal" />
          </span>
          <span>Signal Price</span>
        </a>
        <div className="environment-pill">
          <span className="pulse-dot" />
          Laboratório local
        </div>
      </header>

      <main id="top">
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow">Inteligência de mercado · Evidência real</p>
            <h1>
              O mercado muda.
              <br />
              <em>Você enxerga primeiro.</em>
            </h1>
            <p className="hero-description">
              Descubra ofertas, compare equivalentes e entenda cada exclusão. Sem caixa-preta, sem
              preços inventados.
            </p>
          </div>
          <button
            className="primary-action"
            type="button"
            onClick={collectAll}
            disabled={collectionBusy}
          >
            <span>{collectionBusy ? "Coletando mercado" : "Atualizar mercado"}</span>
            <Icon name={collectionBusy ? "bolt" : "arrow"} />
          </button>
        </section>

        {error ? (
          <div className="error-banner" role="alert">
            <strong>Não foi possível concluir a operação.</strong>
            <span>{error}</span>
            <button type="button" onClick={() => setError(null)}>
              Fechar
            </button>
          </div>
        ) : null}

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
            <p>Fontes observadas</p>
            <strong>{comparison?.source_count ?? successfulSources}</strong>
            <small>de {sources.length} fontes habilitadas</small>
          </article>
          <article className="metric-card">
            <span className="metric-index">04</span>
            <p>Referência</p>
            <strong className="metric-date">
              {formatDate(comparison?.newest_observation_at ?? null)}
            </strong>
            <small>dados sintéticos identificados</small>
          </article>
        </section>

        <div className="workspace-grid">
          <aside className="control-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Coleta</p>
                <h2>Fontes do laboratório</h2>
              </div>
              <Icon name="database" />
            </div>
            <div className="source-list">
              {sources.map((source, index) => {
                const run = runsBySource[source.id];
                const busy = busySourceIds.includes(source.id);
                return (
                  <article className="source-item" key={source.id}>
                    <div className="source-number">0{index + 1}</div>
                    <div className="source-copy">
                      <strong>{source.name.replace(" (lab)", "")}</strong>
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
                          .then(() => {
                            if (selectedVariantId) return loadComparison(selectedVariantId);
                          })
                          .catch((reason: unknown) =>
                            setError(reason instanceof Error ? reason.message : "Falha na coleta"),
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
            </div>
            <p className="lab-note">
              As lojas são aplicações HTTP isoladas. O coletor acessa HTML e JSON-LD reais dentro da
              rede privada do Docker.
            </p>
          </aside>

          <section className="insights-panel">
            <div className="catalog-heading">
              <div>
                <p className="eyebrow">Catálogo canônico</p>
                <h2>{selectedProduct?.name ?? "Nenhum produto"}</h2>
              </div>
              <span className="synthetic-label">Dados sintéticos</span>
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
                      <article className="offer-row" key={offer.offer_id}>
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
                          {offer.payment_terms.installment_count ? (
                            <span>{offer.payment_terms.installment_count}x</span>
                          ) : null}
                          {offer.payment_terms.coupon_code ? (
                            <span>Cupom {offer.payment_terms.coupon_code}</span>
                          ) : null}
                          <span>
                            {offer.shipping.known ? "Frete informado" : "Frete desconhecido"}
                          </span>
                        </div>
                        <strong className="offer-price">{formatMoney(offer.price)}</strong>
                      </article>
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
                <h2>O mercado ainda está silencioso.</h2>
                <p>Execute a primeira coleta para descobrir ofertas e montar a comparação.</p>
                <button
                  type="button"
                  className="secondary-action"
                  onClick={collectAll}
                  disabled={collectionBusy}
                >
                  Iniciar coleta <Icon name="arrow" />
                </button>
              </section>
            )}
          </section>
        </div>
      </main>

      <footer>
        <span>Signal Price · Laboratório de portfólio</span>
        <span>Explicável por desenho, local por padrão.</span>
      </footer>
      <div className="sr-only" aria-live="polite">
        {collectionBusy ? "Coleta em andamento" : (error ?? "Painel atualizado")}
      </div>
    </div>
  );
}
