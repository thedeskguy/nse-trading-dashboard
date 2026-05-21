import { describe, it, expect } from "vitest";
import { VALID_COMBOS, INTRADAY, coercePeriod } from "@/lib/chartRanges";

describe("chartRanges", () => {
  it("keeps period when already valid", () => {
    expect(coercePeriod("1d", "3mo")).toBe("3mo");
    expect(coercePeriod("1m", "1d")).toBe("1d");
  });

  it("coerces invalid period to longest valid one for the interval", () => {
    expect(coercePeriod("1m", "1y")).toBe("5d");
    expect(coercePeriod("5m", "1y")).toBe("1mo");
    expect(coercePeriod("1wk", "1d")).toBe("max");
  });

  it("marks only sub-day intervals as intraday", () => {
    expect(INTRADAY.has("1m")).toBe(true);
    expect(INTRADAY.has("1h")).toBe(true);
    expect(INTRADAY.has("1d")).toBe(false);
    expect(INTRADAY.has("1wk")).toBe(false);
    expect(INTRADAY.has("1mo")).toBe(false);
  });

  it("VALID_COMBOS covers every interval with at least one period", () => {
    for (const [interval, periods] of Object.entries(VALID_COMBOS)) {
      expect(periods.length, `interval ${interval}`).toBeGreaterThan(0);
    }
  });

  it("coerce is idempotent", () => {
    for (const interval of Object.keys(VALID_COMBOS) as Array<keyof typeof VALID_COMBOS>) {
      const coerced = coercePeriod(interval, "1d");
      expect(coercePeriod(interval, coerced)).toBe(coerced);
    }
  });
});
