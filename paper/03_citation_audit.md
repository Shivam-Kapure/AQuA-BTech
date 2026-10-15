# Citation audit

**Audit date:** 2026-09-24

## In-text/reference consistency

The manuscript contains seven numbered in-text references, [1]–[7], and seven corresponding bibliography entries. No reference is used to substantiate an AQUA implementation fact; implementation facts are grounded in repository evidence. The citations support only contextual claims about prior API-testing and agent-testing work.

## Metadata verification

The citation-management metadata tools resolved Crossref or arXiv records for all seed works.

- [1] RESTler: Crossref DOI metadata resolved for `10.1109/ICSE.2019.00083`.
- [2] QuickREST: arXiv metadata resolved for `1912.09686`. Its archival publication record remains to be confirmed before submission.
- [3] EvoMaster: Crossref DOI metadata resolved for `10.21105/joss.02153`.
- [4] APITestGenie: arXiv DOI metadata resolved for `10.48550/arXiv.2409.03838`.
- [5] AutoRestTest: arXiv DOI metadata resolved for `10.48550/arXiv.2501.08600`.
- [6] Agentic LLMs for REST API Test Amplification: arXiv DOI metadata resolved for `10.48550/arXiv.2510.27417`.
- [7] Testing Practices in Open Source AI Agent Frameworks and Agentic Applications: arXiv metadata resolved for `2509.19185`; any archival journal version and DOI must be checked at submission.

`references.bib` contains machine-extracted records for [1] and [3]–[6]; `quickrest.bib` and `hasan.bib` contain the arXiv records for [2] and [7]. The generic BibTeX validator parsed only three entries from the machine-exported `references.bib`, although DOI resolution succeeded for the three parsed arXiv records. Treat the generated BibTeX as a metadata source, not final typeset bibliography input. Normalize all seven entries with the selected IEEE journal template before submission.

## Citation decisions

- The manuscript does not cite papers merely because their titles contain “agentic,” “RAG,” Digital TA, or program assessment. Those topics were screened as adjacent but are not part of the verified AQUA API-testing contribution.
- Preprints are explicitly labeled as preprints. No citation treats them as peer-reviewed archival work.
- Claims about APITestGenie’s reported valid-script rates and the scale of Hasan *et al.*’s empirical corpus are attributed narrowly to those papers; AQUA does not inherit their results.

## Remaining citation tasks

1. Resolve an archival version of QuickREST, if one exists, and replace the arXiv citation.
2. Resolve the final publication metadata for Hasan *et al.* and replace the preprint if appropriate.
3. Re-run a journal-template reference checker after selecting the target venue.
4. Expand the review only through individually verified primary sources; do not inflate the bibliography with unverified search hits.
