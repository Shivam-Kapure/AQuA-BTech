# Scoped literature review: LLM-assisted API testing

**Search date:** 2026-09-24  
**Review type:** targeted, evidence-mapping review for a systems paper; not a PRISMA systematic review.

## Scope and screening

The review covers automated REST/API test generation, OpenAPI-driven testing, LLM-assisted API testing, and testing of agentic applications. It uses implementation relevance as the primary screen. Automated program assessment, Digital Teaching Assistants, and RAG-for-software-engineering were searched as adjacent topics but are excluded from the core synthesis because the audited AQUA implementation does not contain those capabilities.

Searches used title/keyword queries across arXiv, publisher/author pages, and recognized project/publication pages. Included work either (1) evaluates REST/API test generation or (2) supplies a methodological baseline for evaluating LLM/agentic testing. Preprints are labeled as such and must be re-checked for archival versions at submission time.

## Literature matrix

| Work | Problem and approach | Evaluation/evidence | Limitation relevant to AQUA | Relevance |
|---|---|---|---|---|
| Atlidakis, Godefroid, and Polishchuk, “RESTler: Stateful REST API Fuzzing” (ICSE 2019) | Stateful REST API fuzzing from a specification, with dependency-aware request sequencing. | Evaluated on production Azure services and additional APIs. | A rigorous conventional baseline; AQUA needs explicit workflow/dependency evaluation rather than only isolated request generation. | Core traditional baseline. |
| Karlsson, Causevic, and Sundmark, “QuickREST: Property-based Test Generation of OpenAPI-Described RESTful APIs” (2020 preprint) | Generates property-based tests and oracle material from OpenAPI descriptions. | Reports industrial and open-source service experiments and specification/implementation mismatches. | Demonstrates that OpenAPI can support both generation and validation; AQUA must make its oracle/assertion semantics measurable. | Core specification-driven comparator. |
| Arcuri et al., “EvoMaster: A Search-Based System Test Generation Tool” (JOSS 2021) | Search-based, system-level test generation for REST/GraphQL/RPC APIs. | Tool paper with established benchmark and replication ecosystem. | Its stronger empirical norms make simple unit tests insufficient evidence for AQUA. | Core search-based comparator. |
| Pereira, Lima, and Faria, “APITestGenie: Automated API Test Generation through Generative AI” (arXiv 2024) | Uses LLMs to generate executable API test scripts from business requirements and API specifications. | Ten real-world APIs; reports 57% valid scripts on one attempt and 80% after three attempts. | The authors recommend human validation before CI/CD use; AQUA should report validity, repair burden, and execution outcomes rather than only generated cases. | Closest LLM-generation work. |
| Stennett et al., “AutoRestTest: A Tool for Automated REST API Testing Using LLMs and MARL” (arXiv 2025) | Combines a semantic operation-dependency graph, MARL, and specialized agents for operation sequences, parameters, values, dependencies, and headers. | Preliminary tool results; reports telemetry on successful operations, unique server errors, and elapsed time. | AQUA cannot claim an equivalent multi-agent or MARL approach. It can adopt its emphasis on dependency-aware telemetry. | Closest agentic workflow contrast. |
| Besjes et al., “Agentic LLMs for REST API Test Amplification: A Comparative Study Across Cloud Applications” (arXiv 2025) | Compares single- and multi-agent LLM test amplification across cloud APIs. | Studies validity, coverage, defect detection, cost, runtime, energy, and maintainability; the reported multi-agent configuration has trade-offs. | Sets an appropriate evidence bar for any agentic claim. AQUA’s current one-shot decision endpoint does not justify a multi-agent comparison claim. | Evaluation-design guide. |
| Hasan et al., “An Empirical Study of Testing Practices in Open Source AI Agent Frameworks and Agentic Applications” (arXiv 2025; later archival status must be verified) | Mines testing practices in agent frameworks and applications. | 39 frameworks and 439 applications; finds much testing effort targets deterministic tools/workflows rather than FM plan bodies. | Supports testing the deterministic boundaries, prompts, schemas, and workflow contracts separately. It does not validate AQUA’s effectiveness. | Agent-validation context. |

## Thematic synthesis

### Specification-driven and search-based API testing

RESTler, QuickREST, and EvoMaster represent complementary non-LLM baselines. They turn API descriptions, state/dependency information, or search feedback into executable test inputs. Their role in this paper is not merely historical: they establish that a credible evaluation must distinguish operation coverage, stateful workflow coverage, test validity, oracle quality, and fault detection. AQUA currently has specification parsing and deterministic execution, but it has not yet measured any of these outcomes.

### LLM-assisted generation and the executable-test gap

APITestGenie shows that LLM-produced scripts can be useful while still requiring validation and human review. Its reported one-attempt versus repeated-attempt validity figures make executable-test yield a necessary metric for AQUA. AQUA’s operation-membership check is narrower than full semantic correctness: it prevents absent method/path combinations but does not prove correct values, assertions, authentication, or state transitions.

### Agentic approaches and evidence discipline

AutoRestTest and the comparative test-amplification study model substantially richer agentic workflows than AQUA implements. They foreground operation dependencies, outcomes from actual executions, and cost/coverage trade-offs. Therefore, the paper should position AQUA as an auditable LLM-assisted testing platform, not as a multi-agent testing method. The empirical study of agent testing further motivates separate tests for deterministic workflow tools and prompt/model behavior.

## Evidence-supported gap

The defensible gap is not “no tool uses LLMs for API tests.” Prior work clearly does. A narrower, testable systems gap is the need for an auditable integration layer that converts imported API descriptions into constrained LLM-generated candidate cases, runs them through deterministic execution and assertions, persists redacted evidence, supports dependent workflows, and exposes passive security findings. Whether this integration improves testing outcomes remains an experimental question.

## Sources to verify before submission

1. V. Atlidakis, P. Godefroid, and M. Polishchuk, “RESTler: Stateful REST API Fuzzing,” *ICSE*, 2019, doi: 10.1109/ICSE.2019.00083.
2. S. Karlsson, A. Causevic, and D. Sundmark, “QuickREST: Property-based Test Generation of OpenAPI-Described RESTful APIs,” arXiv:1912.09686, 2019. Verify the archival publication details before final references.
3. A. Arcuri, J. P. Galeotti, B. Marculescu, and M. Zhang, “EvoMaster: A Search-Based System Test Generation Tool,” *Journal of Open Source Software*, vol. 6, no. 57, 2021, doi: 10.21105/joss.02153.
4. A. Pereira, B. Lima, and J. P. Faria, “APITestGenie: Automated API Test Generation through Generative AI,” arXiv:2409.03838, 2024, doi: 10.48550/arXiv.2409.03838.
5. T. Stennett, M. Kim, S. Sinha, and A. Orso, “AutoRestTest: A Tool for Automated REST API Testing Using LLMs and MARL,” arXiv:2501.08600, 2025, doi: 10.48550/arXiv.2501.08600.
6. J. Besjes, R. Nooyens, T. Bardakci, M. Beyazit, and S. Demeyer, “Agentic LLMs for REST API Test Amplification: A Comparative Study Across Cloud Applications,” arXiv:2510.27417, 2025, doi: 10.48550/arXiv.2510.27417.
7. M. M. Hasan, H. Li, E. Fallahzadeh, G. K. Rajbahadur, B. Adams, and A. E. Hassan, “An Empirical Study of Testing Practices in Open Source AI Agent Frameworks and Agentic Applications,” arXiv:2509.19185, 2025. Verify any later journal version and DOI before submission.

## Review limitations

This is a curated seed corpus, not an exhaustive systematic-search corpus. Citation metadata for the two works known here only as preprints must be resolved against their publisher records before submission. No claims in the manuscript should rely on papers that have not been individually metadata-verified.
