import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ChartLegend, type LegendRowData } from "@/components/trading-chart/ChartLegend";

const row: LegendRowData = {
  instanceId: "ema-20-close",
  title: "EMA 20",
  lines: [{ lineKey: "line", color: "#2196f3" }],
  hidden: false,
};

const noop = () => {};
const baseProps = {
  volumeVisible: true,
  registerValueEl: noop,
  onToggleHidden: noop,
  onOpenSettings: noop,
  onRemove: noop,
  onToggleVolume: noop,
};

describe("ChartLegend", () => {
  it("renders a row per indicator and a volume row", () => {
    render(<ChartLegend rows={[row]} {...baseProps} />);
    expect(screen.getByText("EMA 20")).toBeInTheDocument();
    expect(screen.getByText("Vol")).toBeInTheDocument();
  });

  it("eye / gear / remove fire callbacks with the instanceId", () => {
    const onToggleHidden = vi.fn();
    const onOpenSettings = vi.fn();
    const onRemove = vi.fn();
    render(
      <ChartLegend rows={[row]} {...baseProps}
        onToggleHidden={onToggleHidden} onOpenSettings={onOpenSettings} onRemove={onRemove} />
    );
    fireEvent.click(screen.getByLabelText("Hide EMA 20"));
    fireEvent.click(screen.getByLabelText("Settings EMA 20"));
    fireEvent.click(screen.getByLabelText("Remove EMA 20"));
    expect(onToggleHidden).toHaveBeenCalledWith("ema-20-close");
    expect(onOpenSettings).toHaveBeenCalledWith("ema-20-close");
    expect(onRemove).toHaveBeenCalledWith("ema-20-close");
  });

  it("volume eye fires onToggleVolume", () => {
    const onToggleVolume = vi.fn();
    render(<ChartLegend rows={[]} {...baseProps} onToggleVolume={onToggleVolume} />);
    fireEvent.click(screen.getByLabelText("Toggle volume"));
    expect(onToggleVolume).toHaveBeenCalledOnce();
  });

  it("hidden rows dim and show the Show label", () => {
    render(<ChartLegend rows={[{ ...row, hidden: true }]} {...baseProps} />);
    expect(screen.getByLabelText("Show EMA 20")).toBeInTheDocument();
  });
});
