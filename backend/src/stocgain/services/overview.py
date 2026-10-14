"""Read-only overview and filtered risk-list services, docs/08 §3.4–3.11."""

from stocgain.api.dependencies import Context, Filters
from stocgain.api.schemas.overview import (
    ActionType,
    CategoryHeatmap,
    HeatmapCategory,
    HeatmapCell,
    HeatmapStore,
    OverviewSummary,
    Recommendations,
    RecommendedAction,
    RiskDistribution,
    RiskPositions,
    RiskTier,
    RiskTrend,
    SortBy,
    SortDirection,
    StoreComparison,
    TopProducts,
)


def summary(ctx: Context, filters: Filters) -> OverviewSummary:
    """Return stored risk and observed operational KPIs for one run and scope."""
    row = ctx.rows("overview_summary", filters.params)[0]
    prior = row["prior_at_risk_positions"]
    row.update(
        as_of_date=ctx.run["as_of_date"],
        run_id=ctx.run["run_id"],
        at_risk_rate=row["at_risk_positions"] / row["active_positions"]
        if row["active_positions"]
        else 0,
        at_risk_positions_change=row["at_risk_positions"] - prior
        if prior is not None
        else None,
        supplier_on_time_window_days=90,
        in_stock_window_days=28,
    )
    return OverviewSummary.model_validate(row)


def distribution(ctx: Context, filters: Filters) -> RiskDistribution:
    """Include zero-count tiers in the documented severity order."""
    rows = ctx.rows("risk_distribution", filters.params)
    return RiskDistribution.model_validate(
        {"tiers": rows, "total_positions": sum(r["positions"] for r in rows)}
    )


def trend(ctx: Context, filters: Filters, weeks: int) -> RiskTrend:
    """Return ascending latest successful runs in the requested week window."""
    return RiskTrend.model_validate(
        {"points": ctx.rows("risk_trend", {**filters.params, "weeks": weeks})}
    )


def stores(ctx: Context, filters: Filters) -> StoreComparison:
    """Compare stores without restricting to the selected stores."""
    return StoreComparison.model_validate(
        {"stores": ctx.rows("store_comparison", filters.params)}
    )


def heatmap(ctx: Context, filters: Filters) -> CategoryHeatmap:
    """Return every store-category combination, including empty cells."""
    rows = ctx.rows("category_heatmap", filters.params)
    store_rows = {
        r["store_id"]: HeatmapStore(store_id=r["store_id"], store_code=r["store_code"])
        for r in rows
    }
    category_rows = {
        r["category_id"]: HeatmapCategory(
            category_id=r["category_id"], category_name=r["category_name"]
        )
        for r in rows
    }
    return CategoryHeatmap(
        stores=list(store_rows.values()),
        categories=list(category_rows.values()),
        cells=[
            HeatmapCell.model_validate(
                {k: v for k, v in r.items() if k not in ("store_code", "category_name")}
            )
            for r in rows
        ],
    )


def top_products(ctx: Context, filters: Filters, limit: int) -> TopProducts:
    """Rank products that have at least one critical or high risk store."""
    return TopProducts.model_validate(
        {"items": ctx.rows("top_products", {**filters.params, "limit": limit})}
    )


def recommendations(
    ctx: Context, filters: Filters, actions: list[RecommendedAction] | None, limit: int
) -> Recommendations:
    """Preserve original global recommendation priority ranks."""
    return Recommendations.model_validate(
        {
            "items": ctx.rows(
                "recommendations",
                {
                    **filters.params,
                    "action_types": actions
                    if actions is not None
                    else ["expedite_po", "reorder", "monitor"],
                    "limit": limit,
                },
            )
        }
    )


def risk_positions(
    ctx: Context,
    filters: Filters,
    risk_tiers: list[RiskTier] | None,
    actions: list[ActionType] | None,
    below_rop: bool | None,
    query: str | None,
    sort_by: SortBy,
    sort_dir: SortDirection | None,
    page: int,
    page_size: int,
) -> RiskPositions:
    """Use bound sorting selectors and return full filtered totals even past last page."""
    direction = sort_dir or (
        "asc"
        if sort_by
        in (
            "priority",
            "product_name",
            "store_code",
            "category_name",
            "next_receipt_date",
        )
        else "desc"
    )
    escaped = (
        query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        if query is not None
        else None
    )
    row = ctx.rows(
        "risk_positions",
        {
            **filters.params,
            "risk_tiers": risk_tiers,
            "action_types": actions,
            "below_reorder_point": below_rop,
            "q": query,
            "q_prefix": escaped + "%" if escaped is not None else None,
            "q_contains": "%" + escaped + "%" if escaped is not None else None,
            "sort_by": sort_by,
            "sort_dir": direction,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        },
    )[0]
    total = row["summary"]["positions"]
    return RiskPositions.model_validate(
        {
            **row,
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size,
        }
    )
