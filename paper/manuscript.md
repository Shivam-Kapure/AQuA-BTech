# AQUA: Schema-Constrained LLM-Assisted API Test Generation With Deterministic Execution and Evidence Management

**Anonymous manuscript draft — target IEEE journal to be selected**

## Abstract

Automated testing of REST APIs must manage heterogeneous request schemas, authentication, state dependencies, and test oracles. Large language models (LLMs) can propose test cases from API descriptions, but unconstrained output is insufficient for dependable execution: a generated case may refer to an unavailable operation, contain invalid input, or use an unsupported assertion. This paper presents AQUA, an LLM-assisted API-testing platform that imports OpenAPI or Postman-derived descriptions, normalizes operations, constrains generated cases to imported method/path pairs, and executes accepted cases through a deterministic HTTP runner. AQUA further supports request assertions, response-value extraction for dependent workflows, redacted run evidence, and passive API-security findings. The platform also contains a separate DOM/RAG-assisted UI-testing path; this paper treats that path as ancillary because it has not yet been evaluated together with the API workflow. The implementation and regression tests establish the availability of the described system components. However, no benchmark evaluation has yet measured generated-case validity, executable-test yield, coverage, defect detection, security-finding precision, runtime, or cost. Accordingly, this draft specifies a reproducible evaluation protocol rather than reporting invented effectiveness results. The planned evaluation compares AQUA against specification-driven baselines on reproducible OpenAPI-described systems and measures generation validity, execution outcomes, workflow completion, coverage, seeded-finding detection, and cost.

**Index Terms—** REST API testing, test-case generation, large language models, OpenAPI, workflow testing, software quality assurance.

## I. Introduction

REST APIs are a central integration boundary in modern software systems. Their test spaces include operation choices, parameter and payload values, authentication contexts, response assertions, and request dependencies. Specification-driven and search-based tools demonstrate that OpenAPI descriptions and state-aware exploration can support automated API testing [1]–[3]. LLMs add a complementary capability: they can transform natural-language and specification context into candidate tests. Nevertheless, generated text is not evidence that a test is executable or useful. APITestGenie, for example, reports that executable-script validity improves with repeated generation attempts and recommends human validation before CI/CD integration [4].

Recent agentic API-testing work explores richer dependency reasoning and multi-agent test amplification [5], [6]. These approaches use explicit dependency modeling or multiple specialized roles and evaluate coverage, defects, and resource trade-offs. AQUA does not implement such a multi-agent architecture. Its repository contains a single LLM decision endpoint for UI-test generation, while its nominal analyzer, planner, executor, and observer modules are empty. The contribution examined in this paper is therefore narrower: an auditable integration workflow for LLM-assisted API-case generation and deterministic execution.

The research problem is how to connect LLM-generated API-test candidates to a controlled execution pipeline without treating unconstrained model output as a trustworthy test artifact. AQUA addresses this problem by normalizing imported operations, rejecting generated method/path pairs outside that catalog, executing accepted cases with deterministic request construction and assertions, recording redacted evidence, and supporting dependent workflows. Passive security analysis is exposed alongside execution results. This design is motivated by the need to make individual generation and execution outcomes inspectable, not by a claim that the system is more effective than existing tools.

This draft makes the following implementation contributions:

1. An OpenAPI/Postman ingestion workflow that produces a normalized catalog of operations, parameters, request and response schemas, base URLs, and declared authentication schemes.
2. An LLM-assisted API-case generator with structural validation that restricts accepted cases to operations present in the imported catalog.
3. A deterministic execution and evidence layer with request assertions, variable substitution, dependent request workflows, redaction, persisted run history, and passive security findings.
4. A claim-centered evaluation protocol that separates implementation validation from effectiveness claims and defines the experiments needed for comparison with established API-testing approaches.

The first three items are supported by repository inspection and regression tests. Any claim of increased coverage, fault detection, validity, security precision, or practical efficiency requires the experiments defined in Section VI.

## II. Related Work

### A. Specification-Driven and Search-Based API Testing

RESTler introduced stateful REST API fuzzing and demonstrated the value of using API specifications to build dependency-aware request sequences [1]. QuickREST generates property-based tests and validation material from OpenAPI documents, highlighting that specifications can serve both generation and oracle roles [2]. EvoMaster provides a search-based system-testing tool for REST, GraphQL, and RPC APIs and has developed an established experimental ecosystem for assessing generated tests [3]. These approaches establish relevant baselines for AQUA: an API-testing evaluation must distinguish syntactic or structural validity from executability, coverage, and fault detection.

### B. LLM-Assisted and Agentic API Testing

APITestGenie generates API test scripts from requirements and API specifications. Its experiments on ten APIs report valid-script rates of 57% for one generation attempt and 80% with three attempts, while retaining a human validation role [4]. AutoRestTest combines an operation-dependency graph, multi-agent reinforcement learning, and LLM-based specialized agents to produce operation sequences and values [5]. Besjes *et al.* compare single- and multi-agent test-amplification configurations across heterogeneous cloud APIs, including execution, coverage, cost, runtime, and energy considerations [6].

These works show that LLM output should be assessed through actual execution and that agentic claims require role-specific implementation and cost-aware evaluation. AQUA is not positioned as a multi-agent alternative to [5] or [6]. Its distinguishing system boundary is the controlled handoff from imported operation descriptions to constrained candidate generation and deterministic execution.

### C. Testing Agentic Systems

Hasan *et al.* study testing practices in agent frameworks and applications and report that deterministic resource and coordination components receive much of the observed testing effort, while prompts receive comparatively little direct testing [7]. This observation motivates AQUA’s separation of model output from deterministic validation, execution, and evidence persistence. It does not establish that AQUA’s validation pipeline improves outcomes; that question remains experimental.

## III. System Scope and Design Goals

### A. Scope

AQUA is implemented as a React/Vite frontend and a FastAPI backend with MongoDB persistence. The paper focuses on the API-testing workflow. The repository also includes UI-test generation, DOM extraction, Chroma-backed retrieval, and Playwright execution. Those components are outside the central experimental scope because no integrated evaluation connects them to the API workflow.

The system is not an automated programming-assessment or Digital TA platform. It does not execute student submissions, grade assignments, generate educational feedback, or use Piston/Supabase. Such capabilities must not be added to the title, abstract, contributions, or evaluation without a separate implementation and study.

### B. Design Goals

The API workflow has four design goals. First, it should preserve an inspectable connection between a test case and the imported API operation catalog. Second, it should execute cases through a deterministic mechanism rather than model-generated request code. Third, it should support practical stateful scenarios through variable extraction and substitution. Fourth, it should persist redacted evidence and security findings so that outcomes can be reviewed rather than treated as opaque LLM decisions.

## IV. AQUA API-Testing Workflow

### A. Specification Ingestion and Normalization

An OpenAPI document is parsed into an `ApiSpec` containing its title, version, base URLs, and normalized `ApiOperation` objects. Each operation records its HTTP method, path, summary, tags, parameters, request schema, response schema, and declared authentication schemes. Postman import is also implemented. This normalized representation is the source of truth for downstream generation and execution.

### B. Constrained LLM Case Generation

For a requested case count, AQUA serializes normalized operations and asks the configured LLM for JSON cases containing a name, method, URL, headers, query values, body, and assertions. Parsed objects are validated against the API-case schema. AQUA then compares each case’s method and path with the imported-operation set and rejects mismatches. This guard establishes structural conformance to the operation catalog; it does not establish that values, semantics, or assertions are correct.

### C. Deterministic Execution and Assertions

The API executor substitutes declared variables into the URL, headers, query, and body; adds configured bearer or basic credentials; validates the target URL; and sends the request with `httpx`. It records status, response headers and body, elapsed time, and assertion outcomes. Implemented assertion kinds cover status, headers, JSON fields, content type, response time, and JSON-schema conformance. Authentication tokens and sensitive evidence fields are redacted before persistence.

### D. Dependent Workflows and Passive Security Findings

API workflow execution can extract response values and pass them to dependent requests. This mechanism is needed for common patterns such as login followed by authenticated state changes. Separately, passive API-security checks inspect declared authentication, static authorization heuristics, CORS/rate-limit headers, server-error responses, documented-schema mismatches, and sensitive-looking response fields. Active probes are explicitly disabled until an isolated-worker policy is implemented.

### E. Ancillary UI-Testing Path

For UI tests, AQUA extracts interactive DOM elements, ingests textual element representations into Chroma, retrieves relevant elements for a test step, and uses that context when requesting a Playwright script. A deterministic fallback exists for supported structured steps. This path is a separate subsystem. It must not be cited as evidence for the API workflow until evaluated under its own protocol.

## V. Research Questions and Methodology

The following research questions are proposed for the completed empirical study.

- **RQ1 (generation validity):** What proportion of AQUA-generated API cases are structurally valid and executable on a fixed corpus of OpenAPI-described APIs?
- **RQ2 (testing effectiveness):** How do AQUA-generated cases compare with a deterministic OpenAPI-template baseline and a selected established API-testing baseline in operation coverage, parameter coverage where measurable, and seeded-fault detection?
- **RQ3 (stateful workflows):** How reliably does AQUA complete predefined dependent workflows requiring extraction, variable substitution, and authentication?
- **RQ4 (passive security findings):** What are the precision and recall of AQUA’s passive security findings against a manually labeled ground truth of seeded conditions?
- **RQ5 (cost and reproducibility):** What latency, token/cost, and resource profiles result from fixed model settings and repeated seeds?

The research artifact must include versioned API specifications, application images or commits, reset scripts, prompts, model identifiers, temperature and token limits, generation counts, random seeds where supported, execution logs with secrets redacted, and per-run outputs. The study should use the included local test target plus at least two independently maintained, reproducible APIs. A deterministic OpenAPI-template generator is a mandatory sanity baseline. A traditional tool such as RESTler, QuickREST, or EvoMaster should be included only where its assumptions and execution environment support a fair comparison; exclusions must be disclosed symmetrically.

## VI. Experimental Setup and Results

### A. Experimental Setup

**[EXPERIMENT REQUIRED]** Freeze the system-under-test corpus, OpenAPI specifications, application versions, API reset procedure, hardware, operating system, Python/Node versions, MongoDB version, and LLM provider/model identifiers. Define identical request and time budgets for every method. Predefine the number of repetitions and report mean, dispersion, and raw per-run outcomes where model nondeterminism is relevant.

**[EXPERIMENT REQUIRED]** Measure: (i) schema/operation-valid generation rate, (ii) executable-test rate, (iii) assertion-pass and failure taxonomy, (iv) operation and parameter coverage, (v) workflow completion rate, (vi) unique seeded defects or labeled security conditions detected, (vii) security precision and recall, and (viii) latency and model-resource use.

**[EXPERIMENT REQUIRED]** Add ablations that remove operation-membership validation and dependent-workflow extraction. These ablations test concrete mechanisms actually implemented by AQUA. Do not add a RAG ablation unless the UI-testing path is included in a separate experiment.

### B. Results

No empirical runs, benchmark corpus, or baseline comparisons are stored in the repository. Therefore, no numerical results are reported in this draft.

**[EXPERIMENT REQUIRED — Table I]** Per-system generation validity, executable-test yield, operation/parameter coverage, and fault-detection results for AQUA and each baseline.

**[EXPERIMENT REQUIRED — Table II]** Dependent-workflow completion results, including authentication and extraction failures.

**[EXPERIMENT REQUIRED — Table III]** Passive-security finding confusion matrices and category-level precision/recall against the ground-truth ledger.

**[EXPERIMENT REQUIRED — Figure 1]** System architecture and controlled data flow: import → normalized operation catalog → LLM case generation → structural validation → deterministic execution/assertions → redacted evidence and findings.

**[EXPERIMENT REQUIRED — Figure 2]** Effectiveness/cost trade-off across methods after experimental data are available.

## VII. Discussion

The implemented design reduces one specific risk of unconstrained LLM output: a case whose method/path does not belong to the imported API catalog is rejected before execution. This is a structural guard, not a semantic guarantee. A case can still contain unsuitable values, invalid authentication, unrealistic state transitions, or weak assertions. Deterministic execution makes such outcomes observable and attributable to a concrete request and assertion result, but it does not by itself demonstrate a higher test yield than existing tools.

The planned comparison must not conflate the platform’s integration features with LLM superiority. Stronger evidence would show when operation constraints increase valid/executable cases, whether dependent workflows improve stateful coverage, and how these benefits trade off against latency and model cost. The passive-security module similarly requires a labeled ground truth: surfacing a warning is not evidence that the warning is correct or useful.

## VIII. Threats to Validity and Limitations

**Construct validity.** Structural operation validation is not equivalent to semantic test correctness. Coverage and fault-detection metrics must be defined before runs and computed consistently across methods.

**Internal validity.** LLM outputs can vary with model version, provider behavior, prompt details, and nondeterministic sampling. The experiment must preserve prompts and model settings, repeat runs, and distinguish generator failures from target-application failures.

**External validity.** The included local social-media target intentionally contains safe, seeded signals and cannot represent production APIs. At least two independent systems, preferably containerized and resettable, are required. Results must not be generalized beyond the evaluated API types and configurations.

**Comparison validity.** RESTler, QuickREST, and EvoMaster differ in required inputs, white-box/black-box assumptions, and generated artifact formats. Comparisons must use a common protocol only where those assumptions align; otherwise, the paper should report the incompatibility rather than forcing a numerical ranking.

**Reproducibility.** The current repository does not include frozen experimental datasets, benchmark scripts, baseline adapters, raw experiment logs, or cost records. These artifacts are prerequisites for a submission-ready empirical paper.

## IX. Conclusion and Future Work

This paper described AQUA as an implemented LLM-assisted API-testing platform with normalized specification ingestion, operation-constrained case generation, deterministic execution and assertions, dependent workflows, redacted evidence persistence, and passive security findings. Repository inspection and regression tests support these implementation claims. They do not yet support comparative claims about effectiveness, coverage, fault detection, security precision, runtime, or cost. The next work is to execute the evaluation protocol with fixed systems and fair baselines, publish the associated artifacts, and revise the Results and Discussion sections using measured evidence only.

## Data Availability

**[REQUIRES EVIDENCE]** The final paper should provide an archival repository URL containing the AQUA source revision, experiment scripts, frozen OpenAPI inputs, baseline adapters, redacted logs, and a results manifest. The repository currently includes a local test target but not a completed experimental artifact package.

## Ethics and Security Statement

The platform performs only passive API-security analysis by default. Active or destructive probes are disabled and should be executed only in explicitly authorized, isolated environments. Experimental APIs must be owned by, publicly designated for testing by, or explicitly authorized by their operators. No student data or human-subject data are used in the current study design.

## CRediT Author Contributions

**[REQUIRES AUTHOR INPUT]** Specify conceptualization, methodology, software, validation, investigation, data curation, writing, visualization, supervision, and project administration contributions using the CRediT taxonomy.

## Conflict of Interest

**[REQUIRES AUTHOR INPUT]** The authors declare no competing interests, or disclose them here.

## Funding

**[REQUIRES AUTHOR INPUT]** State funding support or “This research received no specific grant from any funding agency in the public, commercial, or not-for-profit sectors.”

## AI-Use Disclosure

**[REQUIRES VENUE POLICY AND AUTHOR CONFIRMATION]** This manuscript draft was prepared with AI-assisted literature organization and language editing under author review. Replace this statement with the selected venue’s required disclosure and the authors’ accurate account of tool use.

## References

[1] V. Atlidakis, P. Godefroid, and M. Polishchuk, “RESTler: Stateful REST API Fuzzing,” in *Proceedings of the 41st International Conference on Software Engineering*, 2019, doi: 10.1109/ICSE.2019.00083.

[2] S. Karlsson, A. Causevic, and D. Sundmark, “QuickREST: Property-based Test Generation of OpenAPI-Described RESTful APIs,” arXiv:1912.09686, 2019. **[VERIFY ARCHIVAL VERSION]**

[3] A. Arcuri, J. P. Galeotti, B. Marculescu, and M. Zhang, “EvoMaster: A Search-Based System Test Generation Tool,” *Journal of Open Source Software*, vol. 6, no. 57, p. 2153, 2021, doi: 10.21105/joss.02153.

[4] A. Pereira, B. Lima, and J. P. Faria, “APITestGenie: Automated API Test Generation through Generative AI,” arXiv:2409.03838, 2024, doi: 10.48550/arXiv.2409.03838.

[5] T. Stennett, M. Kim, S. Sinha, and A. Orso, “AutoRestTest: A Tool for Automated REST API Testing Using LLMs and MARL,” arXiv:2501.08600, 2025, doi: 10.48550/arXiv.2501.08600.

[6] J. Besjes, R. Nooyens, T. Bardakci, M. Beyazit, and S. Demeyer, “Agentic LLMs for REST API Test Amplification: A Comparative Study Across Cloud Applications,” arXiv:2510.27417, 2025, doi: 10.48550/arXiv.2510.27417.

[7] M. M. Hasan, H. Li, E. Fallahzadeh, G. K. Rajbahadur, B. Adams, and A. E. Hassan, “An Empirical Study of Testing Practices in Open Source AI Agent Frameworks and Agentic Applications,” arXiv:2509.19185, 2025. **[VERIFY ARCHIVAL VERSION AND DOI]**
