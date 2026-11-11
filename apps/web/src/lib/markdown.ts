import React, { useEffect } from "react";

export interface ParsedSource {
  index: number;
  title: string;
  url: string;
  domain?: string;
}

/**
 * Escapes backslashes and brackets inside Markdown link text to avoid breaking link syntax.
 */
export function escapeMarkdownTitle(title: string): string {
  return title.replace(/\\/g, "\\\\").replace(/[[\]]/g, "\\$&");
}

/**
 * Generates a clean URL slug from heading text compatible with standard GFM anchors.
 * Preserves Unicode letters and numbers while removing punctuation (including connector punctuation like underscores),
 * without collapsing repeated hyphens.
 */
export function slugify(text: string): string {
  return text
    .toString()
    .trim()
    .toLowerCase()
    .replace(/[^\p{L}\p{M}\p{N}\s-]/gu, "")
    .replace(/\s/g, "-")
    .replace(/^-+/, "")
    .replace(/-+$/, "");
}

/**
 * Returns primary slug and, if applicable, a secondary slug without leading numbering.
 * E.g. "1. Introduction" -> ["1-introduction", "introduction"]
 */
export function getHeadingSlugs(text: string): string[] {
  const clean = text.trim();
  const primary = slugify(clean);
  const withoutNumber = slugify(clean.replace(/^\d+[\.\)\-]?\s*/, ""));
  if (withoutNumber && withoutNumber !== primary) {
    return [primary, withoutNumber];
  }
  return [primary];
}

/**
 * Extracts plain text from nested React children.
 */
export function getNodeText(node: React.ReactNode): string {
  if (node === null || node === undefined || typeof node === "boolean") {
    return "";
  }
  if (typeof node === "string" || typeof node === "number") {
    return String(node);
  }
  if (Array.isArray(node)) {
    return node.map(getNodeText).join("");
  }
  if (
    React.isValidElement(node) &&
    node.props &&
    (node.props as { children?: React.ReactNode }).children
  ) {
    return getNodeText((node.props as { children?: React.ReactNode }).children);
  }
  return "";
}

/**
 * Extracts plain text from a unified/remark AST node.
 */
export function extractAstText(node: any): string {
  if (!node) return "";
  if (typeof node.value === "string") return node.value;
  if (Array.isArray(node.children)) {
    return node.children.map(extractAstText).join("");
  }
  return "";
}

/**
 * Remark plugin to compute stable, occurrence-based heading IDs directly from the markdown AST.
 * This guarantees IDs are deterministic and never mutated by React component rerenders.
 */
export function remarkHeadingSlugs() {
  return (tree: any) => {
    const allocatedIds = new Set<string>();
    function visit(node: any) {
      if (node.type === "heading") {
        const text = extractAstText(node);
        const rawSlugs = getHeadingSlugs(text);
        const baseSlug = rawSlugs[0] || "section";

        let primaryId = baseSlug;
        let suffix = 0;
        while (allocatedIds.has(primaryId)) {
          suffix += 1;
          primaryId = `${baseSlug}-${suffix}`;
        }
        allocatedIds.add(primaryId);

        const secondarySlugs: string[] = [];
        for (const slug of rawSlugs.slice(1)) {
          if (slug && slug !== primaryId && !allocatedIds.has(slug)) {
            secondarySlugs.push(slug);
            allocatedIds.add(slug);
          }
        }

        node.data = node.data || {};
        node.data.hProperties = node.data.hProperties || {};
        node.data.hProperties.id = primaryId;
        if (secondarySlugs.length > 0) {
          node.data.hProperties["data-secondary-slugs"] =
            secondarySlugs.join(",");
        }
      }
      if (Array.isArray(node.children)) {
        node.children.forEach(visit);
      }
    }
    visit(tree);
  };
}

/**
 * Extracts a hostname/domain for display from a URL string.
 */
export function extractDomain(url: string): string {
  try {
    const parsed = new URL(url);
    return parsed.hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

/**
 * Smoothly scrolls to an element by its ID or hash, respecting prefers-reduced-motion
 * and safely handling malformed URI components.
 * For user-initiated navigation (options.focusTarget = true), moves keyboard focus to the target
 * element to keep navigation accessible.
 */
export function scrollToHashTarget(
  hashOrId: string,
  options?: { pushState?: boolean; focusTarget?: boolean } | boolean,
): boolean {
  if (typeof window === "undefined" || !hashOrId) return false;
  const pushState =
    typeof options === "boolean" ? options : Boolean(options?.pushState);
  const focusTarget =
    typeof options === "object" ? Boolean(options?.focusTarget) : false;

  try {
    const rawId = hashOrId.startsWith("#") ? hashOrId.slice(1) : hashOrId;
    const targetId = decodeURIComponent(rawId);
    if (!targetId) return false;
    const targetEl = document.getElementById(targetId);
    if (targetEl) {
      const prefersReducedMotion =
        typeof window.matchMedia === "function" &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      targetEl.scrollIntoView({
        behavior: prefersReducedMotion ? "auto" : "smooth",
        block: "start",
      });
      if (pushState) {
        window.history.pushState(null, "", `#${targetId}`);
      }
      if (focusTarget) {
        const headingId = targetEl.getAttribute("data-heading-id");
        const focusEl =
          (headingId ? document.getElementById(headingId) : null) || targetEl;
        if (!focusEl.hasAttribute("tabindex")) {
          focusEl.setAttribute("tabindex", "-1");
        }
        focusEl.focus({ preventScroll: true });
      }
      return true;
    }
  } catch {
    // Ignore malformed URI components
  }
  return false;
}

/**
 * React hook to automatically scroll to the URL hash once content is ready,
 * and listen for subsequent hashchange events without artificial fixed delays.
 * Page-load scrolling keeps focus unchanged.
 */
export function useHashNavigation(isReady: boolean): void {
  useEffect(() => {
    if (!isReady || typeof window === "undefined") return;

    const onHashChange = () => {
      if (window.location.hash) {
        scrollToHashTarget(window.location.hash, {
          pushState: false,
          focusTarget: false,
        });
      }
    };

    if (window.location.hash) {
      if (
        !scrollToHashTarget(window.location.hash, {
          pushState: false,
          focusTarget: false,
        })
      ) {
        requestAnimationFrame(() => {
          scrollToHashTarget(window.location.hash, {
            pushState: false,
            focusTarget: false,
          });
        });
      }
    }

    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, [isReady]);
}

/**
 * Normalizes research reports so that:
 * 1. Headings and Table of Contents anchors align properly.
 * 2. Unlinked or parenthetical citations (e.g., "(Stanford HAI)", "(IBM; Google Cloud)", "[1]")
 *    are converted into interactive in-text bracketed citations: "[[1]](#source-1)".
 * 3. The "## Sources" section is cleanly structured as a numbered list with citation anchors and links.
 */
export function normalizeReportMarkdown(text: string): {
  normalized: string;
  sources: ParsedSource[];
} {
  if (!text || typeof text !== "string") {
    return { normalized: "", sources: [] };
  }

  // Find Sources or References section
  const sourcesSectionRegex =
    /(?:^|\n)(##?\s+(?:Sources|References)\b[^\n]*\n)([\s\S]*?)(?=\n##|\n#[^#]|$)/i;
  const sourcesMatch = text.match(sourcesSectionRegex);

  if (!sourcesMatch || sourcesMatch.index === undefined) {
    return { normalized: text, sources: [] };
  }

  const header = sourcesMatch[1];
  const sourcesContent = sourcesMatch[2];
  const sourcesStart =
    sourcesMatch.index + (sourcesMatch[0].startsWith("\n") ? 1 : 0);

  // Parse source entries
  const rawLines = sourcesContent.split("\n").filter((l) => l.trim().length > 0);
  const sources: ParsedSource[] = [];

  for (let i = 0; i < rawLines.length; i++) {
    const line = rawLines[i].trim();
    const explicit = line.match(/^(?:\[\[)?(\d+)(?:[.)\]]|\]\])/);
    const index = explicit ? parseInt(explicit[1], 10) : sources.length + 1;

    // Markdown link: [Title](URL) or 1. [Title](URL) or [[1]](#source-1) [Title](URL)
    // Supports one level of balanced parentheses in the URL
    const mdLink = line.match(
      /(?:\[\[?\d+\]?\]\(#[^)]+\)\s*)?\[([^\]]+)\]\((https?:\/\/(?:[^\s()]|\([^\s()]*\))+)\)/,
    );
    if (mdLink) {
      sources.push({
        index,
        title: mdLink[1].trim(),
        url: mdLink[2].trim(),
        domain: extractDomain(mdLink[2].trim()),
      });
      continue;
    }

    // Text with URL: - Title: URL or 1. Title: URL or Title - URL
    const namedUrl = line.match(
      /^(?:[-*•\d\.\)]+\s*)(.*?)(?::\s*|\s*-\s*|\s+)(https?:\/\/(?:[^\s()]|\([^\s()]*\))+)/,
    );
    if (namedUrl) {
      sources.push({
        index,
        title: namedUrl[1].trim(),
        url: namedUrl[2].trim(),
        domain: extractDomain(namedUrl[2].trim()),
      });
      continue;
    }

    // Text with parenthesized or bracketed URL: 1. Title (https://...) or 1. Title <https://...>
    const parenUrl = line.match(
      /^(?:[-*•\d\.\)]+\s*)(.*?)\s*[<(](https?:\/\/(?:[^\s()<>]|\([^\s()]*\))+)[>)]/,
    );
    if (parenUrl) {
      sources.push({
        index,
        title: parenUrl[1].trim() || `Source ${index}`,
        url: parenUrl[2].trim(),
        domain: extractDomain(parenUrl[2].trim()),
      });
      continue;
    }

    // Bare URL
    const bareUrl = line.match(/(https?:\/\/(?:[^\s()]|\([^\s()]*\))+)/);
    if (bareUrl) {
      sources.push({
        index,
        title: `Source ${index}`,
        url: bareUrl[1].trim(),
        domain: extractDomain(bareUrl[1].trim()),
      });
    }
  }

  if (sources.length === 0) {
    return { normalized: text, sources: [] };
  }

  const validIndexes = new Set(sources.map((s) => s.index));

  // Build title lookup for matching parenthetical citations
  const titleToSource = new Map<string, ParsedSource>();
  for (const s of sources) {
    if (s.title) {
      titleToSource.set(s.title.toLowerCase(), s);
      const clean = s.title.toLowerCase().replace(/^[^\w]+|[^\w]+$/g, "");
      if (clean) titleToSource.set(clean, s);
    }
  }

  // Process the body content before ## Sources outside fenced code and inline code
  let body = text.slice(0, sourcesStart);
  const citationRe =
    /(?<!\[)(?<!\!)\[([1-9]\d*(?:\s*,\s*[1-9]\d*)*)\](?!\()(?!:)/g;

  body = body
    .split(/(```[\s\S]*?```|`[^`\n]+`)/)
    .map((segment, idx) => {
      if (idx % 2 === 1) {
        return segment; // Code block or span: leave untouched
      }

      // 1. Replace parenthetical citations like "(Stanford HAI)" or "(IBM; Google Cloud)"
      let processed = segment.replace(
        /\(([^()\n]{2,80})\)/g,
        (fullMatch, inner) => {
          const parts = inner.split(/[;,]\s*/).map((p: string) => p.trim());
          const matched: ParsedSource[] = [];
          for (const part of parts) {
            const s = titleToSource.get(part.toLowerCase());
            if (s) {
              matched.push(s);
            }
          }
          if (matched.length > 0 && matched.length === parts.length) {
            return matched
              .map((m) => `[[${m.index}]](#source-${m.index})`)
              .join(" ");
          }
          return fullMatch;
        },
      );

      // 2. Replace unlinked bracket citations like "[1]" or "[1, 2]"
      processed = processed.replace(citationRe, (fullMatch, nums) => {
        const splitNums = nums
          .split(/\s*,\s*/)
          .map((n: string) => parseInt(n, 10))
          .filter((n: number) => !isNaN(n));
        if (
          splitNums.length > 0 &&
          splitNums.every((n: number) => validIndexes.has(n))
        ) {
          return splitNums
            .map((n: number) => `[[${n}]](#source-${n})`)
            .join(" ");
        }
        return fullMatch;
      });

      return processed;
    })
    .join("");

  // 3. Format the ## Sources section into clean numbered items with source anchors
  let newSourcesSection = `${header}\n`;
  for (const s of sources) {
    newSourcesSection += `${s.index}. [[${s.index}]](#source-${s.index}) [${escapeMarkdownTitle(s.title)}](${s.url})\n`;
  }
  newSourcesSection += "\n";

  const afterSources = text.slice(sourcesStart + sourcesMatch[0].length);
  return {
    normalized: `${body}${newSourcesSection}${afterSources}`,
    sources,
  };
}
