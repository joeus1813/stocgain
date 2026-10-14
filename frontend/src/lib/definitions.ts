export const definitions = {
  active:
    "Active store–SKU positions in the current analytics run. Source: PostgreSQL current risk snapshot.",
  risk: "Critical and High positions at the model cutoff. Estimated checkpoint stockout probability; not a realized stockout count.",
  margin:
    "Model estimate of expected lost units × unit gross margin in the binding protection window. Not realized loss or an annual forecast.",
  cover:
    "Median on-hand inventory / expected daily demand across positions with positive demand. No recent demand is shown as —.",
  supplier:
    "Purchase orders first received by the promised date / all POs due in the last 90 days, including overdue orders.",
  stock:
    "Share of position-days with positive closing stock over the last 28 days. Source: observed inventory snapshots.",
  probability:
    "Estimated probability that demand exceeds available supply at the riskiest replenishment checkpoint.",
  policy:
    "Recommended stock levels from the persisted model. Decision support only; no purchase orders are created.",
  scenario:
    "The same model is recalculated. Service level and buffer change policy targets, not current stock or near-term risk.",
} as const;
