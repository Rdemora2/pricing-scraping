import { formatDelta, formatMoney, formatStorage } from "../formatters";
import type { Product, ProductIntelligence } from "../types";

type ProductIntelligencePanelProps = {
  product: Product | null;
  intelligence: ProductIntelligence | null;
};

export function ProductIntelligencePanel({ product, intelligence }: ProductIntelligencePanelProps) {
  if (!product || !intelligence) return null;

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
          <p className="eyebrow">Visão consolidada do aparelho</p>
          <h2 id="model-intelligence-title">O que os dados dizem sobre o {product.name}</h2>
          <p>
            Leitura entre capacidades e cores, sempre comparando primeiro a mesma configuração.
            Ausência de preço é tratada como lacuna de cobertura, não como preço zero.
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
            {intelligence.observed_variant_count}/{intelligence.catalog_variant_count} configurações
            com preço · {intelligence.retailer_count} varejistas
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
              : "Ainda faltam capacidades comparáveis."}
          </p>
        </article>
        <article className="intelligence-card">
          <span>Faixa total observada</span>
          <strong>{formatMoney(intelligence.min_price)}</strong>
          <p>
            {intelligence.max_price
              ? `até ${formatMoney(intelligence.max_price)} em ${intelligence.total_offer_count} ofertas`
              : "Nenhum preço comparável nesta janela."}
          </p>
        </article>
        <article className="intelligence-card">
          <span>Cor com menor índice relativo</span>
          <strong>
            {intelligence.cheapest_color?.color.replaceAll("-", " ") ?? "Em formação"}
          </strong>
          <p>
            {intelligence.cheapest_color
              ? `${formatDelta(intelligence.cheapest_color.relative_price_delta_pct)} versus cores da mesma capacidade`
              : "Sem equivalência suficiente entre cores."}
          </p>
        </article>
      </div>

      <details className="dimension-details">
        <summary>Explorar análise por capacidade e cor</summary>
        <div className="dimension-grid">
          <section>
            <div className="dimension-heading">
              <h3>Por armazenamento</h3>
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
                    <span>Cores observadas</span>
                    <b>
                      {item.observed_variant_count}/{item.catalog_variant_count}
                    </b>
                  </div>
                </article>
              ))}
            </div>
          </section>
          <section>
            <div className="dimension-heading">
              <h3>Por cor</h3>
              <span>normalizada por capacidade</span>
            </div>
            <div className="dimension-list">
              {intelligence.color_analysis.map((item) => (
                <article key={item.color}>
                  <strong>{item.color.replaceAll("-", " ")}</strong>
                  <div>
                    <span>Índice relativo</span>
                    <b>{formatDelta(item.relative_price_delta_pct)}</b>
                  </div>
                  <div>
                    <span>Capacidades comparáveis</span>
                    <b>{item.comparable_storage_count}</b>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </div>
      </details>
      <details className="methodology-panel">
        <summary>Metodologia e critérios de confiança</summary>
        <ul>
          {intelligence.methodology.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </details>
    </section>
  );
}
