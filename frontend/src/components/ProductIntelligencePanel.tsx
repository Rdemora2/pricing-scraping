import { formatDelta, formatMoney, formatStorage } from "../formatters";
import type { Product, ProductIntelligence } from "../types";

type ProductIntelligencePanelProps = {
  product: Product | null;
  intelligence: ProductIntelligence | null;
};

export function ProductIntelligencePanel({ product, intelligence }: ProductIntelligencePanelProps) {
  if (!product || !intelligence) return null;

  const firstStorage = intelligence.storages_gb.at(0);
  const lastStorage = intelligence.storages_gb.at(-1);
  const storageRange =
    firstStorage !== undefined && lastStorage !== undefined
      ? `${formatStorage(firstStorage)} a ${formatStorage(lastStorage)}`
      : "não informado";
  const statusLabel = {
    no_data: "Aguardando mercado",
    limited: "Amostra limitada",
    developing: "Cobertura em formação",
    strong: "Amostra robusta",
  }[intelligence.sample_status];

  return (
    <section className="model-intelligence" aria-labelledby="model-intelligence-title">
      <div className="intelligence-lead">
        <div>
          <p className="eyebrow">Leitura executiva</p>
          <h2 id="model-intelligence-title">{product.name}, explicado.</h2>
          <p>
            O catálogo acompanha {intelligence.storages_gb.length} capacidades, de {storageRange}, e{" "}
            {intelligence.colors.length} cores: {intelligence.colors.join(", ") || "não informadas"}
            . A inteligência usa apenas preços comparáveis da mesma variante.
          </p>
        </div>
        <div
          className="coverage-gauge"
          role="progressbar"
          aria-label="Cobertura das variantes"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={intelligence.coverage_pct}
        >
          <span>{intelligence.coverage_pct}%</span>
          <small>{statusLabel}</small>
          <div>
            <i style={{ width: `${intelligence.coverage_pct}%` }} />
          </div>
          <p>
            {intelligence.observed_variant_count}/{intelligence.catalog_variant_count} variantes ·{" "}
            {intelligence.retailer_count} varejistas
          </p>
        </div>
      </div>

      <div className="intelligence-cards">
        <article className="intelligence-card intelligence-card-signal">
          <span>Melhor custo por capacidade</span>
          <strong>
            {intelligence.best_value_storage
              ? formatStorage(intelligence.best_value_storage.storage_gb)
              : "Em formação"}
          </strong>
          <p>
            {intelligence.best_value_storage?.price_per_gb
              ? `${formatMoney(intelligence.best_value_storage.price_per_gb)} por GB`
              : "Precisamos observar ao menos duas capacidades."}
          </p>
        </article>
        <article className="intelligence-card">
          <span>Cor relativamente mais barata</span>
          <strong>{intelligence.cheapest_color?.color ?? "Em formação"}</strong>
          <p>
            {intelligence.cheapest_color
              ? `${formatDelta(intelligence.cheapest_color.relative_price_delta_pct)} contra a mediana das cores da mesma capacidade`
              : "Sem combinações equivalentes suficientes."}
          </p>
        </article>
        <article className="intelligence-card">
          <span>Cor relativamente mais cara</span>
          <strong>{intelligence.most_expensive_color?.color ?? "Em formação"}</strong>
          <p>
            {intelligence.most_expensive_color
              ? `${formatDelta(intelligence.most_expensive_color.relative_price_delta_pct)} contra a mediana das cores da mesma capacidade`
              : "Sem combinações equivalentes suficientes."}
          </p>
        </article>
        <article className="intelligence-card">
          <span>Faixa encontrada</span>
          <strong>{formatMoney(intelligence.min_price)}</strong>
          <p>
            {intelligence.max_price
              ? `até ${formatMoney(intelligence.max_price)} em ${intelligence.total_offer_count} ofertas comparáveis`
              : "Nenhum preço comparável até agora."}
          </p>
        </article>
      </div>

      <div className="dimension-grid">
        <section>
          <div className="dimension-heading">
            <h3>Inteligência por armazenamento</h3>
            <span>mediana entre cores</span>
          </div>
          <div className="dimension-list">
            {intelligence.storage_analysis.map((item) => (
              <article key={item.storage_gb}>
                <strong>{formatStorage(item.storage_gb)}</strong>
                <div>
                  <span>Preço representativo</span>
                  <b>{formatMoney(item.representative_price)}</b>
                </div>
                <div>
                  <span>Custo por GB</span>
                  <b>{formatMoney(item.price_per_gb)}</b>
                </div>
                <small>
                  {item.observed_variant_count}/{item.catalog_variant_count} cores observadas
                </small>
              </article>
            ))}
          </div>
        </section>
        <section>
          <div className="dimension-heading">
            <h3>Inteligência por cor</h3>
            <span>normalizada por capacidade</span>
          </div>
          <div className="dimension-list">
            {intelligence.color_analysis.map((item) => (
              <article key={item.color}>
                <strong>{item.color}</strong>
                <div>
                  <span>Índice relativo</span>
                  <b>{formatDelta(item.relative_price_delta_pct)}</b>
                </div>
                <div>
                  <span>Faixa observada</span>
                  <b>{item.min_price ? `${formatMoney(item.min_price)}+` : "—"}</b>
                </div>
                <small>{item.comparable_storage_count} capacidades comparáveis</small>
              </article>
            ))}
          </div>
        </section>
      </div>
      <details className="methodology-panel">
        <summary>Como calculamos estes insights</summary>
        <ul>
          {intelligence.methodology.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </details>
    </section>
  );
}
