import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MethodologyNote } from "@/components/analysis/MethodologyNote";

describe("MethodologyNote", () => {
  it("renders the default summary title", () => {
    render(<MethodologyNote>Some explanation</MethodologyNote>);
    expect(screen.getByText("How this is computed")).toBeInTheDocument();
  });

  it("renders custom title and body content", () => {
    render(<MethodologyNote title="Backtest method">Walk-forward, no look-ahead.</MethodologyNote>);
    expect(screen.getByText("Backtest method")).toBeInTheDocument();
    expect(screen.getByText("Walk-forward, no look-ahead.")).toBeInTheDocument();
  });
});
