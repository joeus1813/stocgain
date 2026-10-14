"use client";
import { useState } from "react";
import type { Schema } from "@/lib/api/client";
import {
  formatCount,
  formatDecimal,
  formatRate,
  formatLabel,
  formatDate,
} from "@/lib/format";
import { Card } from "./shared/ui";
import { QueryPanel } from "./shared/query-panel";
export function ForecastEvaluation({ compact = false }: { compact?: boolean }) {
  const [basis, setBasis] = useState("observed_in_stock"),
    [segment, setSegment] = useState(compact ? "overall" : "horizon_bucket");
  return (
    <Card
      title="Forecast evaluation"
      subtitle="Actual stored rolling-origin backtest measurements"
    >
      <div className="risk-controls">
        <label>
          Basis{" "}
          <select
            aria-label="Evaluation basis"
            value={basis}
            onChange={(e) => setBasis(e.target.value)}
          >
            <option value="observed_in_stock">Observed in-stock sales</option>
            <option value="simulated_latent">
              Simulation-only hidden demand
            </option>
          </select>
        </label>
        {!compact && (
          <label>
            Segment{" "}
            <select
              aria-label="Evaluation segment"
              value={segment}
              onChange={(e) => setSegment(e.target.value)}
            >
              {[
                "overall",
                "horizon_bucket",
                "velocity_class",
                "demand_pattern",
              ].map((v) => (
                <option key={v} value={v}>
                  {formatLabel(v)}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      <QueryPanel<Schema<"Evaluation">>
        path={`/forecasts/evaluation?segment_type=${segment}&evaluation_basis=${basis}`}
      >
        {(d) => (
          <>
            <p className="chart-note">{d.notes[basis]}</p>
            <p className="chart-note">
              {formatCount(d.n_origins)} historical origins ·{" "}
              {formatDate(d.first_origin_date)} –{" "}
              {formatDate(d.last_origin_date)}
            </p>
            {d.rows.length ? (
              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Model</th>
                      <th>Segment</th>
                      <th>Observations</th>
                      <th>MAE (units)</th>
                      <th>WAPE</th>
                      <th>Bias</th>
                    </tr>
                  </thead>
                  <tbody>
                    {d.rows.map((r) => (
                      <tr key={`${r.model_name}-${r.segment_value}`}>
                        <td>
                          {r.model_name === "stocgain_v1"
                            ? "stocgain"
                            : formatLabel(r.model_name)}
                        </td>
                        <td>{r.segment_value}</td>
                        <td>{formatCount(r.n_observations)}</td>
                        <td>{formatDecimal(r.mae)}</td>
                        <td>{formatRate(r.wape)}</td>
                        <td>{formatRate(r.bias_rate)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="empty">
                No evaluation rows are available for this run and segment.
              </p>
            )}
            <p className="chart-note">
              WAPE = sum of absolute errors / sum of actual demand. Positive
              bias indicates overforecasting. These simulated results are not
              evidence of real-world business impact.
            </p>
          </>
        )}
      </QueryPanel>
    </Card>
  );
}
