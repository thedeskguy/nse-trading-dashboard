import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SystemsStrip } from "@/components/analysis/SystemsStrip";

describe("SystemsStrip", () => {
  it("renders all three system verdicts", () => {
    render(
      <SystemsStrip
        technical={{ signal: "BUY", confidence: 72 }}
        fundamental={{ grade: "Strong", score: 70 }}
        ml={{ direction: "UP", probability: 0.62 }}
        onSelectTab={() => {}}
      />
    );
    expect(screen.getByText("BUY · 72%")).toBeInTheDocument();
    expect(screen.getByText("Strong · 70")).toBeInTheDocument();
    expect(screen.getByText("UP · 62%")).toBeInTheDocument();
  });

  it("navigates to the tab on click", () => {
    const onSelect = vi.fn();
    render(
      <SystemsStrip
        technical={{ signal: "BUY", confidence: 72 }}
        fundamental={null}
        ml={null}
        onSelectTab={onSelect}
      />
    );
    fireEvent.click(screen.getByText("Technical"));
    expect(onSelect).toHaveBeenCalledWith("technical");
  });

  it("shows placeholders for missing systems", () => {
    render(<SystemsStrip technical={null} fundamental={null} ml={null} onSelectTab={() => {}} />);
    expect(screen.getAllByText("—")).toHaveLength(3);
  });
});
