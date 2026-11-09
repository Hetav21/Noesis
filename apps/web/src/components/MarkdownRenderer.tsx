"use client";

import React, { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  normalizeReportMarkdown,
  getHeadingSlugs,
  getNodeText,
  extractDomain,
} from "@/lib/markdown";
import { ExternalLink, Copy, Check, Hash } from "lucide-react";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  className = "",
}) => {
  const [copiedCodeIndex, setCopiedCodeIndex] = useState<number | null>(null);

  const { normalized } = useMemo(() => {
    return normalizeReportMarkdown(content);
  }, [content]);

  const handleScrollToTarget = (href: string) => {
    if (!href.startsWith("#")) return;
    const targetId = decodeURIComponent(href.slice(1));
    const el = document.getElementById(targetId);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      window.history.pushState(null, "", href);
    }
  };

  const handleCopyCode = async (codeText: string, index: number) => {
    try {
      await navigator.clipboard.writeText(codeText);
      setCopiedCodeIndex(index);
      setTimeout(() => setCopiedCodeIndex(null), 2000);
    } catch (err) {
      console.error("Failed to copy code", err);
    }
  };

  return (
    <div className={`markdown-body max-w-none ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children, ...props }) => {
            const text = getNodeText(children);
            const slugs = getHeadingSlugs(text);
            const primaryId = slugs[0];
            const secondarySlugs = slugs.filter((s) => s !== primaryId);

            return (
              <div className="relative group/h1">
                {secondarySlugs.map((slug) => (
                  <span
                    key={slug}
                    id={slug}
                    className="scroll-mt-24 pointer-events-none"
                    aria-hidden="true"
                  />
                ))}
                <h1
                  id={primaryId}
                  className="scroll-mt-24 text-2xl sm:text-3xl font-bold tracking-tight text-white leading-tight mt-8 mb-4 pb-2 border-b border-white/[0.08] flex items-center justify-between"
                  {...props}
                >
                  <span>{children}</span>
                  {primaryId && (
                    <a
                      href={`#${primaryId}`}
                      onClick={(e) => {
                        e.preventDefault();
                        handleScrollToTarget(`#${primaryId}`);
                      }}
                      className="opacity-0 group-hover/h1:opacity-100 text-zinc-500 hover:text-zinc-200 transition-opacity p-1"
                      title="Copy section link"
                      aria-label="Link to section"
                    >
                      <Hash className="w-4 h-4" />
                    </a>
                  )}
                </h1>
              </div>
            );
          },

          h2: ({ children, ...props }) => {
            const text = getNodeText(children);
            const slugs = getHeadingSlugs(text);
            const primaryId = slugs[0];
            const secondarySlugs = slugs.filter((s) => s !== primaryId);

            return (
              <div className="relative group/h2">
                {secondarySlugs.map((slug) => (
                  <span
                    key={slug}
                    id={slug}
                    className="scroll-mt-24 pointer-events-none"
                    aria-hidden="true"
                  />
                ))}
                <h2
                  id={primaryId}
                  className="scroll-mt-24 text-xl sm:text-2xl font-semibold tracking-tight text-zinc-100 mt-8 mb-3 pb-1.5 border-b border-white/[0.04] flex items-center justify-between"
                  {...props}
                >
                  <span>{children}</span>
                  {primaryId && (
                    <a
                      href={`#${primaryId}`}
                      onClick={(e) => {
                        e.preventDefault();
                        handleScrollToTarget(`#${primaryId}`);
                      }}
                      className="opacity-0 group-hover/h2:opacity-100 text-zinc-500 hover:text-zinc-200 transition-opacity p-1"
                      title="Copy section link"
                      aria-label="Link to section"
                    >
                      <Hash className="w-4 h-4" />
                    </a>
                  )}
                </h2>
              </div>
            );
          },

          h3: ({ children, ...props }) => {
            const text = getNodeText(children);
            const slugs = getHeadingSlugs(text);
            const primaryId = slugs[0];
            const secondarySlugs = slugs.filter((s) => s !== primaryId);

            return (
              <div className="relative group/h3">
                {secondarySlugs.map((slug) => (
                  <span
                    key={slug}
                    id={slug}
                    className="scroll-mt-24 pointer-events-none"
                    aria-hidden="true"
                  />
                ))}
                <h3
                  id={primaryId}
                  className="scroll-mt-24 text-lg font-semibold text-zinc-200 mt-6 mb-2.5 flex items-center justify-between"
                  {...props}
                >
                  <span>{children}</span>
                  {primaryId && (
                    <a
                      href={`#${primaryId}`}
                      onClick={(e) => {
                        e.preventDefault();
                        handleScrollToTarget(`#${primaryId}`);
                      }}
                      className="opacity-0 group-hover/h3:opacity-100 text-zinc-500 hover:text-zinc-200 transition-opacity p-1"
                      title="Copy section link"
                      aria-label="Link to section"
                    >
                      <Hash className="w-3.5 h-3.5" />
                    </a>
                  )}
                </h3>
              </div>
            );
          },

          h4: ({ children, ...props }) => {
            const text = getNodeText(children);
            const slugs = getHeadingSlugs(text);
            const primaryId = slugs[0];

            return (
              <h4
                id={primaryId}
                className="scroll-mt-24 text-base font-semibold text-zinc-300 mt-4 mb-2"
                {...props}
              >
                {children}
              </h4>
            );
          },

          a: ({ href, children, ...props }) => {
            if (!href) return <a {...props}>{children}</a>;

            // Citation badge link (e.g. #source-1)
            if (href.startsWith("#source-")) {
              const sourceNum = href.replace("#source-", "");
              return (
                <a
                  href={href}
                  onClick={(e) => {
                    e.preventDefault();
                    handleScrollToTarget(href);
                  }}
                  className="citation-badge scroll-mt-24"
                  title={`Source [${sourceNum}]`}
                  {...props}
                >
                  {children}
                </a>
              );
            }

            // Internal anchor navigation link (e.g. Table of Contents link)
            if (href.startsWith("#")) {
              return (
                <a
                  href={href}
                  onClick={(e) => {
                    e.preventDefault();
                    handleScrollToTarget(href);
                  }}
                  className="text-zinc-300 hover:text-white underline decoration-white/20 hover:decoration-white transition-colors cursor-pointer"
                  {...props}
                >
                  {children}
                </a>
              );
            }

            // External link
            const domain = extractDomain(href);
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="group/link inline-flex items-center gap-1 text-zinc-100 hover:text-white underline decoration-white/30 hover:decoration-white transition-colors break-words font-medium"
                {...props}
              >
                <span>{children}</span>
                {domain && (
                  <span className="no-underline inline-flex items-center gap-0.5 px-1.5 py-0.2 text-[10px] font-mono text-zinc-400 bg-white/[0.05] rounded border border-white/[0.08]">
                    {domain}
                    <ExternalLink className="w-2.5 h-2.5 opacity-70 group-hover/link:opacity-100" />
                  </span>
                )}
              </a>
            );
          },

          pre: ({ children, ...props }) => {
            const codeText = getNodeText(children);
            const codeIndex = Math.abs(
              codeText.split("").reduce((acc, c) => (acc * 31 + c.charCodeAt(0)) | 0, 0),
            );

            return (
              <div className="relative group/code my-5 rounded-xl border border-white/[0.08] bg-[#101014] overflow-hidden">
                <div className="flex items-center justify-between px-4 py-2 border-b border-white/[0.06] bg-zinc-900/40 text-[11px] font-mono text-zinc-400">
                  <span>code</span>
                  <button
                    type="button"
                    onClick={() => handleCopyCode(codeText, codeIndex)}
                    className="inline-flex items-center gap-1 text-zinc-400 hover:text-white transition-colors cursor-pointer"
                  >
                    {copiedCodeIndex === codeIndex ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-400" />
                        <span className="text-emerald-400">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
                <pre
                  className="p-4 overflow-x-auto text-xs sm:text-sm font-mono text-zinc-200 leading-relaxed bg-transparent"
                  {...props}
                >
                  {children}
                </pre>
              </div>
            );
          },

          table: ({ children, ...props }) => (
            <div className="my-6 overflow-x-auto rounded-xl border border-white/[0.08] bg-[#101014]">
              <table className="w-full text-left text-sm border-collapse" {...props}>
                {children}
              </table>
            </div>
          ),

          thead: ({ children, ...props }) => (
            <thead
              className="bg-zinc-900/80 text-zinc-200 border-b border-white/[0.08]"
              {...props}
            >
              {children}
            </thead>
          ),

          th: ({ children, ...props }) => (
            <th
              className="px-4 py-3 font-semibold text-xs uppercase tracking-wider text-zinc-300 border-b border-white/[0.08]"
              {...props}
            >
              {children}
            </th>
          ),

          td: ({ children, ...props }) => (
            <td
              className="px-4 py-3 text-zinc-300 border-b border-white/[0.04]"
              {...props}
            >
              {children}
            </td>
          ),

          blockquote: ({ children, ...props }) => (
            <blockquote
              className="my-5 border-l-2 border-zinc-500 bg-white/[0.02] pl-4 py-2.5 pr-4 text-zinc-400 italic rounded-r-lg"
              {...props}
            >
              {children}
            </blockquote>
          ),

          ul: ({ children, ...props }) => (
            <ul
              className="my-3 space-y-1.5 list-disc list-inside text-zinc-300 pl-2 leading-relaxed"
              {...props}
            >
              {children}
            </ul>
          ),

          ol: ({ children, ...props }) => (
            <ol
              className="my-3 space-y-1.5 list-decimal list-inside text-zinc-300 pl-2 leading-relaxed"
              {...props}
            >
              {children}
            </ol>
          ),

          li: ({ children, ...props }) => {
            let sourceId: string | undefined;
            if (Array.isArray(children) && children.length > 0) {
              const first = children[0];
              if (
                React.isValidElement(first) &&
                first.props &&
                typeof (first.props as { href?: string }).href === "string" &&
                (first.props as { href?: string }).href!.startsWith("#source-")
              ) {
                sourceId = (first.props as { href?: string }).href!.slice(1);
              }
            }

            return (
              <li
                id={sourceId}
                className={`text-zinc-300 marker:text-zinc-500 ${sourceId ? "scroll-mt-24 p-1 -ml-1 rounded transition-colors" : ""}`}
                {...props}
              >
                {children}
              </li>
            );
          },

          hr: ({ ...props }) => (
            <hr className="my-8 border-white/[0.08]" {...props} />
          ),
        }}
      >
        {normalized}
      </ReactMarkdown>
    </div>
  );
};
