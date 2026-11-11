import { describe, it, expect } from "bun:test";
import { normalizeReportMarkdown, slugify, getHeadingSlugs } from "../markdown";

describe("markdown normalization", () => {
  it("normalizes markdown links in Sources section", () => {
    const raw = `# Title
## Table of Contents
1. [Intro](#intro)
2. [Sources](#sources)

## Intro
Solid-state batteries are promising [1] while sodium-ion offers lower costs [2].

## Sources
1. [Solid-state Batteries Overview](https://example.com/ssb)
2. [Sodium-ion Market 2024](https://example.com/na-ion)
`;
    const { normalized, sources } = normalizeReportMarkdown(raw);
    expect(sources).toHaveLength(2);
    expect(sources[0].title).toBe("Solid-state Batteries Overview");
    expect(sources[0].url).toBe("https://example.com/ssb");
    expect(sources[1].title).toBe("Sodium-ion Market 2024");
    expect(sources[1].url).toBe("https://example.com/na-ion");

    // In-text citations should be transformed into clickable badges
    expect(normalized).toContain("[[1]](#source-1)");
    expect(normalized).toContain("[[2]](#source-2)");

    // Sources list should contain anchor tags and markdown links
    expect(normalized).toContain("1. [[1]](#source-1) [Solid-state Batteries Overview](https://example.com/ssb)");
    expect(normalized).toContain("2. [[2]](#source-2) [Sodium-ion Market 2024](https://example.com/na-ion)");
  });

  it("normalizes parenthesized and named URLs in Sources section", () => {
    const raw = `## Sources
1. Battery Council (https://example.com/bc)
2. Energy Insights: https://example.com/ei
`;
    const { sources } = normalizeReportMarkdown(raw);
    expect(sources).toHaveLength(2);
    expect(sources[0].title).toBe("Battery Council");
    expect(sources[0].url).toBe("https://example.com/bc");
    expect(sources[1].title).toBe("Energy Insights");
    expect(sources[1].url).toBe("https://example.com/ei");
  });

  it("slugifies headings correctly removing punctuation without collapsing hyphens", () => {
    expect(slugify("Data_Set")).toBe("dataset");
    expect(slugify("1. Introduction")).toBe("1-introduction");
    expect(getHeadingSlugs("1. Introduction")).toEqual(["1-introduction", "introduction"]);
  });
});
