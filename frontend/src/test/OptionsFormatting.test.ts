import { describe, it, expect } from "vitest";

// Mirror the formatting helpers from the options components
function fmtOI(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
  return String(v);
}

function fmt(v: number, decimals = 2): string {
  if (!v && v !== 0) return "—";
  return v.toLocaleString("en-IN", { maximumFractionDigits: decimals });
}

describe("OI formatting", () => {
  it("formats millions", () => {
    expect(fmtOI(2_500_000)).toBe("2.5M");
  });

  it("formats thousands", () => {
    expect(fmtOI(45_000)).toBe("45K");
  });

  it("passes small numbers through unchanged", () => {
    expect(fmtOI(750)).toBe("750");
  });
});

describe("Price formatting", () => {
  it("returns em dash for falsy non-zero", () => {
    expect(fmt(null as any)).toBe("—");
    expect(fmt(undefined as any)).toBe("—");
  });

  it("formats zero as 0 (not em dash)", () => {
    expect(fmt(0)).toBe("0");
  });

  it("formats a number with decimals", () => {
    expect(fmt(22450.5)).toContain("22");
  });
});
