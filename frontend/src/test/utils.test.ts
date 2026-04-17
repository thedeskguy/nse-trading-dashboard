import { describe, it, expect } from "vitest";
import { cn } from "@/lib/utils";

describe("cn (class merge utility)", () => {
  it("merges class names", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("deduplicates conflicting Tailwind classes (last wins)", () => {
    expect(cn("text-red-500", "text-blue-500")).toBe("text-blue-500");
  });

  it("handles conditional classes", () => {
    expect(cn("base", false && "skipped", "included")).toBe("base included");
  });

  it("handles undefined/null gracefully", () => {
    expect(cn("a", undefined, null as any, "b")).toBe("a b");
  });
});
