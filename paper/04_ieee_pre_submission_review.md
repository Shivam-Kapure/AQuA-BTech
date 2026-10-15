# IEEE-style pre-submission review

**Detected axes:** venue_type=generic; review_scope=full-manuscript; domain=ai-ml; strictness=harsh.  
**Assessment boundary:** the evidence-bounded manuscript draft in `manuscript.md`; no measured experiment results, target-venue instructions, figures, or author metadata were supplied.

## Major rejection risks

1. **[Critical] No empirical evidence supports the central effectiveness questions.** The manuscript appropriately discloses this limitation, but a journal paper cannot be submitted with its Results section consisting of planned tables. Execute the experiment package in `01_project_and_experiment_audit.md` before submission.
2. **[Critical] Novelty remains unproven against close systems.** The current contribution is an implementation integration. Without a direct comparison against at least a deterministic OpenAPI baseline and a compatible established API-testing tool, a reviewer can reasonably view it as a routine engineering combination.
3. **[Critical] No ground-truth security evaluation exists.** Passive warnings are not equivalent to valid findings. Establish a public, manually labeled seeded-condition ledger and report precision/recall by category.
4. **[Major] The target IEEE venue is unspecified.** Scope, article length, template, anonymity, data/code policy, and AI-use disclosure cannot be finalized without the journal’s current author instructions.
5. **[Major] The closest agentic literature is not a valid basis for an agentic claim.** The manuscript corrects this issue by explicitly excluding a multi-agent claim, but the title/abstract and future revisions must preserve that boundary.
6. **[Major] Experiment reproducibility is not yet an artifact.** Frozen target versions, reset scripts, prompts, model identifiers, request budgets, seeds, baseline adapters, and redacted raw outputs are missing.

## Technical review

- **Scope:** The systems-paper scope is plausible for a software-engineering or IEEE software venue, but target-fit cannot be assessed until a journal is named.
- **Novelty:** The manuscript correctly avoids claiming that LLM API testing is new. Its potential contribution is the auditable constraint/execution/evidence integration. A contribution table contrasting AQUA with APITestGenie, AutoRestTest, RESTler, QuickREST, and EvoMaster is required after verifying feature support from primary sources.
- **Validity:** The code supports the implementation description. Regression tests and frontend builds show project health, not testing effectiveness. Empty role modules make any multi-agent terminology invalid.
- **Data and experiments:** No benchmark data or fair baselines are available. The proposed evaluation plan is appropriately claim-centered, but every reported number remains an experiment requirement.
- **Clarity:** The manuscript has a clear implementation/evidence distinction and defines the API-testing boundary. The terminology “LLM-assisted,” “schema-constrained,” and “deterministic execution” should remain consistent in figures and tables.
- **Compliance:** Data availability, author contributions, funding, conflict, and AI-use statements remain placeholders. Resolve them against the chosen venue policy. Use IEEE’s template and reference/PDF checking tools at finalization.
- **Advancement:** The work can advance the field only if controlled evidence shows a useful trade-off relative to established approaches. An integrated product alone is unlikely to meet a technical-journal advancement threshold.

## Presentation review

- **[Major]** The architecture and result figures are placeholders. Create a readable vector architecture diagram that separates the API workflow from the ancillary UI/RAG path.
- **[Major]** No results tables exist. Do not create them until the experimental data and baseline protocols are fixed.
- **[Minor]** Replace the anonymous header with the target journal’s author, affiliation, and corresponding-author format after double-blind requirements are known.
- **[Minor]** Normalize the final bibliography from machine-extracted records using the target template; retain preprint labels where no archival publication is verified.

## Revision applied to this draft

The manuscript has already been revised to address the risks that can be fixed without new data: it removes Digital TA and multi-agent claims, labels all absent results as `[EXPERIMENT REQUIRED]`, narrows contributions to implemented mechanisms, separates the UI/RAG path from the API evaluation scope, and labels unresolved bibliographic/author-policy items. The Critical evidence gaps cannot be repaired through writing.

## Bounded decision posture

The manuscript is a rigorous planning and systems-description draft, not a submission-ready empirical journal article. Its readiness depends on completing the Critical experiment, comparison, and reproducibility work above.
