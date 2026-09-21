import { formatMoney, formatStorage } from "../formatters";
import type { ProductIntelligence, Variant } from "../types";

type VariantNavigatorProps = {
  variants: Variant[];
  intelligence: ProductIntelligence | null;
  selectedVariantId: string | null;
  onSelect: (variantId: string) => void;
};

function normalizedColor(color: string): string {
  return color.replaceAll("-", " ");
}

export function VariantNavigator({
  variants,
  intelligence,
  selectedVariantId,
  onSelect,
}: VariantNavigatorProps) {
  const selectedVariant = variants.find((item) => item.id === selectedVariantId) ?? variants[0];
  const selectedStorage = selectedVariant?.attributes.storage_gb;
  const storages = intelligence?.storage_analysis ?? [];
  const coverageByVariant = new Map(
    (intelligence?.variant_analysis ?? []).map((item) => [item.variant_id, item]),
  );
  const colors = variants.filter((item) => item.attributes.storage_gb === selectedStorage);

  const selectStorage = (storage: number) => {
    const candidates = variants.filter((item) => Number(item.attributes.storage_gb) === storage);
    const bestObserved = candidates
      .map((variant) => ({ variant, coverage: coverageByVariant.get(variant.id) }))
      .sort(
        (left, right) =>
          (right.coverage?.retailer_count ?? 0) - (left.coverage?.retailer_count ?? 0) ||
          (right.coverage?.offer_count ?? 0) - (left.coverage?.offer_count ?? 0),
      )[0]?.variant;
    if (bestObserved) onSelect(bestObserved.id);
  };

  return (
    <section className="variant-configurator" aria-labelledby="variant-configurator-title">
      <div className="configurator-heading">
        <div>
          <p className="eyebrow">Configuração analisada</p>
          <h3 id="variant-configurator-title">Escolha capacidade e acabamento</h3>
        </div>
        <p>
          Cada opção mostra a cobertura coletada agora. Configurações sem evidência continuam
          visíveis, mas não entram nos indicadores.
        </p>
      </div>

      <fieldset className="choice-group storage-choice-group">
        <legend>
          <span>1</span> Armazenamento
        </legend>
        <div className="storage-options">
          {storages.map((storage) => {
            const isSelected = Number(selectedStorage) === storage.storage_gb;
            return (
              <button
                key={storage.storage_gb}
                type="button"
                className={isSelected ? "storage-option active" : "storage-option"}
                aria-pressed={isSelected}
                onClick={() => selectStorage(storage.storage_gb)}
              >
                <strong>{formatStorage(storage.storage_gb)}</strong>
                <span>
                  {storage.observed_variant_count}/{storage.catalog_variant_count} cores com preço
                </span>
                <small>
                  {storage.representative_price
                    ? `mediana ${formatMoney(storage.representative_price)}`
                    : "sem evidência recente"}
                </small>
              </button>
            );
          })}
        </div>
      </fieldset>

      <fieldset className="choice-group color-choice-group">
        <legend>
          <span>2</span> Cor
        </legend>
        <div className="color-options">
          {colors.map((variant) => {
            const coverage = coverageByVariant.get(variant.id);
            const isSelected = variant.id === selectedVariantId;
            const offerCount = coverage?.offer_count ?? 0;
            return (
              <button
                key={variant.id}
                type="button"
                className={isSelected ? "color-option active" : "color-option"}
                aria-pressed={isSelected}
                onClick={() => onSelect(variant.id)}
              >
                <span className="color-option-name">
                  <i aria-hidden="true" />
                  <strong>{normalizedColor(variant.attributes.color ?? "Não informada")}</strong>
                </span>
                <span className={offerCount > 0 ? "coverage-count ready" : "coverage-count empty"}>
                  {offerCount > 0
                    ? `${offerCount} ${offerCount === 1 ? "oferta" : "ofertas"}`
                    : "sem ofertas"}
                </span>
                <small>
                  {coverage?.median_price
                    ? `mediana ${formatMoney(coverage.median_price)}`
                    : "aguardando coleta desta configuração"}
                </small>
              </button>
            );
          })}
        </div>
      </fieldset>
    </section>
  );
}
