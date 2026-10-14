import { render, screen, fireEvent } from "@testing-library/react";
import { it, expect, vi } from "vitest";
import { Tier, Probability, Kpi } from "@/components/shared/ui";
import { AssumptionControl } from "@/components/scenario/assumption-control";
it("uses labels as well as color for risk and estimated KPIs", () => {
  render(
    <>
      <Tier tier="critical" />
      <Probability value={0.75} tier="critical" />
      <Kpi label="Est. gross margin at risk" value="$149" definition="margin" />
    </>,
  );
  expect(screen.getByText("Critical")).toBeVisible();
  expect(screen.getByText("75.0%")).toBeVisible();
  expect(screen.getByText("$149")).toBeVisible();
  expect(
    screen.getByTitle(/Model estimate of expected lost units/),
  ).toBeVisible();
});
it("assumption inputs expose invalid values and synchronize range changes", () => {
  const change = vi.fn();
  const { rerender } = render(
    <AssumptionControl
      label="Lead time"
      value="0"
      min={-7}
      max={14}
      step={1}
      changed={false}
      onChange={change}
    />,
  );
  fireEvent.change(screen.getByRole("slider"), { target: { value: "4" } });
  expect(change).toHaveBeenCalledWith("4");
  rerender(
    <AssumptionControl
      label="Lead time"
      value="30"
      min={-7}
      max={14}
      step={1}
      changed
      onChange={change}
    />,
  );
  expect(screen.getByRole("alert")).toHaveTextContent("between -7 and 14");
  expect(screen.getByRole("spinbutton")).toHaveAttribute(
    "aria-invalid",
    "true",
  );
});

import { Action } from "@/components/shared/ui";
it("does not make an additional reorder quantity look like an expedite PO number", () => {
  render(<Action action="expedite_po" units={222} />);
  expect(screen.getByText("Expedite PO", { exact: true })).toBeVisible();
});
