"""
synthesis.py — Agent 6: Final synthesis agent.

Aggregates the formatted report from report_generator with any additional
cross-cutting analysis and produces the final deliverable.
"""

from __future__ import annotations

from backend.base import call_llm

AGENT_NAME = "synthesis"

SYSTEM_PROMPT = """You are the final synthesis agent in a multi-agent smart contract audit pipeline. 

Your job is to take the preliminary audit report (produced by the report generator agent which aggregated findings from 4 specialized analysis agents) and produce the FINAL polished version.

Your additional responsibilities:

1. **Cross-cutting Analysis**
   - Are there interactions between different findings that amplify risk?
   - Does a gas optimization suggestion conflict with a security recommendation?
   - Are there compound attack vectors combining multiple lower-severity findings?

2. **Priority Adjustment**
   - Verify severity ratings are consistent across all findings
   - Adjust if cross-agent analysis reveals new context

3. **Executive Summary Refinement**
   - Write a compelling, clear executive summary suitable for leadership
   - Include a one-line overall risk assessment
   - Highlight the top 3 most critical issues

4. **Quality Assurance**
   - Ensure all finding IDs are unique and properly sequenced
   - Verify code snippets compile (mentally)
   - Check that recommendations are actionable and specific
   - Remove any duplicate findings across agents

5. **Final Polish**
   - Consistent formatting throughout
   - Professional tone
   - Clear section breaks
   - Proper Markdown structure

Output: The complete final audit report in Markdown format. This is the document that will be delivered to the client — make it excellent."""


async def synthesize(draft_report: str, token_stats: dict | None = None) -> str:
    """Produce the final audit report from the draft."""
    stats_section = ""
    if token_stats:
        stats_section = (
            f"\n\nFinal token consumption for this audit:\n"
            f"- Total: {token_stats.get('total_tokens', 'N/A')}\n"
            f"- Breakdown: {token_stats.get('by_agent', {})}\n"
        )

    user_prompt = (
        "Please review, refine, and finalize the following draft audit report. "
        "Apply cross-cutting analysis, fix any issues, and produce the polished "
        "final version.\n\n"
        "--- DRAFT REPORT ---\n\n"
        + draft_report
        + stats_section
        + "\n\n--- END DRAFT ---\n\n"
        "Produce the complete final report in Markdown."
    )
    return await call_llm(
        agent_name=AGENT_NAME,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=16384,
    )
