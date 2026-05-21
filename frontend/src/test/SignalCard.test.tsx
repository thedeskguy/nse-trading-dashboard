import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SignalCard } from "@/components/analysis/SignalCard";
import type { SignalResponse } from "@/lib/api/market";

const baseSignal: SignalResponse = {
  ticker: "RELIANCE.NS",
  signal: "BUY",
  confidence: 72,
  last_price: 2450.5,
  stop_loss: 2380.0,
  target: 2580.0,
  components: {},
};

describe("SignalCard", () => {
  it("renders BUY signal with confidence", () => {
    render(<SignalCard data={baseSignal} />);
    expect(screen.getByText("BUY")).toBeInTheDocument();
    expect(screen.getByText("72%")).toBeInTheDocument();
  });

  it("renders SELL signal", () => {
    render(<SignalCard data={{ ...baseSignal, signal: "SELL", confidence: 65 }} />);
    expect(screen.getByText("SELL")).toBeInTheDocument();
    expect(screen.getByText("65%")).toBeInTheDocument();
  });

  it("renders HOLD signal", () => {
    render(<SignalCard data={{ ...baseSignal, signal: "HOLD", confidence: 48 }} />);
    expect(screen.getByText("HOLD")).toBeInTheDocument();
  });

  it("shows entry, stop-loss and target price labels", () => {
    render(<SignalCard data={baseSignal} />);
    expect(screen.getByText("Entry")).toBeInTheDocument();
    expect(screen.getByText("Stop Loss")).toBeInTheDocument();
    expect(screen.getByText("Target")).toBeInTheDocument();
  });
});
