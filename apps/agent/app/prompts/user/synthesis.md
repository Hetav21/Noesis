<research_inquiry>
{topic}
</research_inquiry>

<research_configuration>
  <depth>{depth}</depth>
  <breadth>{breadth}</breadth>
  <target_scope>{scope_desc}</target_scope>
  <scope_directives>
{scope_directives}
  </scope_directives>
</research_configuration>

<evidence_base count="{source_count}">
{sources_block}
</evidence_base>

<task_directive>
Synthesize the evidence base above into a comprehensive, authoritative research report answering the research inquiry in full alignment with the target scope.
Structure the report starting with `# Title`, followed immediately by `## Table of Contents` with kebab-case anchor slugs, detailed thematic sections, and a finalized `## Sources` section.
</task_directive>

<formatting_reminder>
CRITICAL STRUCTURAL CHECKLIST BEFORE GENERATION:
1. Every factual assertion, metric, benchmark, and technical claim in the report body MUST have an in-text bracket citation (e.g., [1], [2], [1, 3]) matching the source numbers above. Parenthetical author names like (IBM) or (Wikipedia) are strictly prohibited.
2. The Table of Contents must use exact kebab-case anchor slugs (lowercase, spaces to hyphens, punctuation stripped) and must terminate with `[Sources](#sources)`.
3. The report MUST conclude with a `## Sources` section where EVERY entry is a numbered markdown link: `1. [Exact Source Title](URL)`. Never use plain text titles or bare URLs.
4. Begin immediately with `# [Report Title]` without any conversational preamble, pleasantries, or introductory remarks.
</formatting_reminder>
