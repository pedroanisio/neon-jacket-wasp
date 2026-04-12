# Project: Neon Jacket Wasp

Silhouette analysis SDK with v4 JSON schema (27 sections), Pydantic models, fluent builder API, and enrichment pipeline.

## LLM Output Verification -- Architectural Requirement
## (PALS's LAW)

**Principle authored by:** Pedro Anisio de Luna e Silva
**PALS_LAW_VERSION:** 1.5.4

For any model M and realistic task distribution D:

    E[e(M(x), x)] >= d > 0

Every pipeline, agent, or workflow that accepts LLM
output MUST treat that output as untrusted, incomplete,
and unverified by default. Verification is not optional
post-processing -- it is a first-class design concern.

> Absence of a verification layer is a design defect,
> regardless of how correct the LLM output appears to be.

### Error taxonomy (9 classes, PALS's Law section 5)

| Class | Identifier | SDK coverage |
|---|---|---|
| Hallucination | `ERR_HALLUCINATION` | Not covered |
| Omission | `ERR_OMISSION` | Covered (Pydantic required fields) |
| Schema violation | `ERR_SCHEMA` | Covered (Pydantic strict mode) |
| Truncation | `ERR_TRUNCATION` | Covered (min_length constraints) |
| Sycophancy | `ERR_SYCOPHANCY` | Not covered |
| Instruction failure | `ERR_INSTRUCTION` | Not covered |
| Calibration failure | `ERR_CALIBRATION` | Not covered |
| Semantic drift | `ERR_SEMANTIC` | Not covered |
| Reasoning failure | `ERR_REASONING` | Not covered |

### Architectural corollaries

1. **Appearance of correctness is not correctness** (section 8.1) -- passing tests on sample data does not prove error-freedom.
2. **Trust accumulation is prohibited** (section 8.2) -- do not relax verification after observing correct outputs.
3. **Verification scope must match error taxonomy** (section 8.3) -- checking only `ERR_SCHEMA` does not cover `ERR_HALLUCINATION`.
4. **Silent acceptance is an architectural defect** (section 8.4) -- passing LLM output without a declared verification boundary is a blocking defect.
5. **Capability growth shifts the verification problem, not away from it** (section 8.5).

### Programmatic access

```python
from lib.builder import SilhouetteDocument

doc = SilhouetteDocument.from_json("output.json")
report = doc.verification_report()
print(report.covered_classes)    # {ERR_SCHEMA, ERR_OMISSION, ERR_TRUNCATION}
print(report.uncovered_classes)  # {ERR_HALLUCINATION, ERR_SYCOPHANCY, ...}
print(report.passed)             # True if no schema errors detected
```
