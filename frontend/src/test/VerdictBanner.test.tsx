import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { VerdictBanner, classifyVerdict } from "@/components/analysis/VerdictBanner";

describe("classifyVerdict", () => {
  it("maps high scores to bullish", () => {
    expect(classifyVerdict(80)).toBe("BULLISH");
    expect(classifyVerdict(60)).toBe("BULLISH");
  });

  it("maps low scores to bearish", () => {
    expect(classifyVerdict(20)).toBe("BEARISH");
    expect(classifyVerdict(40)).toBe("BEARISH");
  });

  it("maps mid scores to neutral", () => {
    expect(classifyVerdict(50)).toBe("NEUTRAL");
    expect(classifyVerdict(null)).toBe("NEUTRAL");
    expect(classifyVerdict(undefined)).toBe("NEUTRAL");
  });
});

describe("VerdictBanner", () => {
  it("renders bullish label and score", () => {
    render(<VerdictBanner verdict="BULLISH" headline="Strong uptrend" score={72} />);
    expect(screen.getByText(/Bullish Outlook/i)).toBeInTheDocument();
    expect(screen.getByText("Strong uptrend")).toBeInTheDocument();
    expect(screen.getByText("72")).toBeInTheDocument();
  });

  it("renders bearish label", () => {
    render(<VerdictBanner verdict="BEARISH" headline="Weak fundamentals" />);
    expect(screen.getByText(/Bearish Outlook/i)).toBeInTheDocument();
  });

  it("renders neutral label with optional sublabel", () => {
    render(
      <VerdictBanner verdict="NEUTRAL" headline="Mixed signals" sublabel="watch next close" />,
    );
    expect(screen.getByText(/Neutral Outlook/i)).toBeInTheDocument();
    expect(screen.getByText("watch next close")).toBeInTheDocument();
  });
});
