import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MLPredictionCard, FEATURE_LABELS } from "@/components/analysis/MLPredictionCard";
import type { MLResponse } from "@/lib/api/analysis";

const baseML: MLResponse = {
  ticker: "RELIANCE.NS",
  direction: "UP",
  probability: 0.62,
  accuracy: 0.55,
  feature_importance: { rsi: 0.2, ema200_dist: 0.15, ret_5d: 0.1 },
  train_samples: 180,
  test_samples: 45,
  error: null,
};

describe("MLPredictionCard", () => {
  it("renders direction, probability and accuracy context", () => {
    render(<MLPredictionCard data={baseML} onBacktestModel={() => {}} />);
    expect(screen.getByText("UP")).toBeInTheDocument();
    expect(screen.getByText("62%")).toBeInTheDocument();
    expect(screen.getByText(/55% accuracy on the last 45 sessions/)).toBeInTheDocument();
  });

  it("maps feature keys to readable labels", () => {
    expect(FEATURE_LABELS.ema200_dist).toBe("Distance from EMA 200");
    render(<MLPredictionCard data={baseML} onBacktestModel={() => {}} />);
    expect(screen.getByText("Distance from EMA 200")).toBeInTheDocument();
  });

  it("fires onBacktestModel when the button is clicked", () => {
    const onBacktest = vi.fn();
    render(<MLPredictionCard data={baseML} onBacktestModel={onBacktest} />);
    fireEvent.click(screen.getByText(/Backtest this model/));
    expect(onBacktest).toHaveBeenCalledOnce();
  });
});
