const currencyFormatter = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

const dateFormatter = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

export function formatMoney(value: string | null): string {
  return value === null ? "—" : currencyFormatter.format(Number(value));
}

export function formatDate(value: string | null): string {
  return value === null ? "Sem coleta" : dateFormatter.format(new Date(value));
}

export function formatStorage(value: number): string {
  return value >= 1024 ? `${value / 1024} TB` : `${value} GB`;
}

export function formatDelta(value: string | null): string {
  if (value === null) return "Sem base comparável";
  const numeric = Number(value);
  const prefix = numeric > 0 ? "+" : "";
  return `${prefix}${numeric.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%`;
}
