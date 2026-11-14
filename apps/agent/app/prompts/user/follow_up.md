<research_inquiry>
{topic}
</research_inquiry>

<progress_status>
  <current_iteration>{iteration}</current_iteration>
  <target_depth>{depth}</target_depth>
  <total_sources_accumulated>{total_sources}</total_sources_accumulated>
</progress_status>

<evidence_base>
{recent_findings}
</evidence_base>

<task_directive>
Audit the evidence base gathered so far against the research inquiry and current progress (Iteration {iteration} of {depth}).
Determine whether the evidence thoroughly addresses all dimensions of the topic or if further investigation is required.
If gaps remain and Iteration < Target Depth, provide detailed analytical reasoning and 2-4 focused, keyword-dense follow-up queries targeting the missing dimensions.
If depth has been satisfied or all essential questions are answered, set should_follow_up to false.
</task_directive>
