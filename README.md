# Coordinate Guard

A native C++17 library and CLI for one small but consequential preprocessing contract: apply a sequence edit at an explicit coordinate, verify the reference allele, and report the result in a declared orientation.

Independent portfolio prototype inspired by the correctness and reproducibility requirements of RNA-model workflows. **No Deep Genomics integration, proprietary model access, RNA prediction, pathogenicity interpretation, or clinical validation is implemented or claimed.** All included data is authored synthetic DNA.

## Build and run

Requirements: C++17 compiler (`g++`/`c++`), GNU Make, and Python 3.9+ for independent verification. No runtime packages, CMake, GPU, account, or network connection are needed.

```sh
make
./build/coordinate-guard --sequence ACGT --position 2 --coordinates one --ref C --alt T --strand +
make test
make evaluate
```

The example produces `ATGT`. `make evaluate` runs the same meaningful test suite and writes an environment-labeled measurement to `benchmarks/local-verification.json`. The tracked sample is a local run, not a claim that GitHub Actions has executed.

Other examples:

```sh
# Insert AA after the last base: boundary 4 on a four-base sequence.
./build/coordinate-guard --sequence ACGT --position 4 --coordinates zero --ref - --alt AA --strand +

# Delete CC from the forward reference, then reverse-complement the edited result.
./build/coordinate-guard --sequence AACCGG --position 3 --coordinates one --ref CC --alt - --strand -
```

## The coordinate contract

| Input | Exact meaning |
| --- | --- |
| `--sequence` | Nonempty forward-orientation sequence, uppercase A/C/G/T only; maximum one million bases in the library contract |
| `--coordinates zero` | Position is a zero-based start offset |
| `--coordinates one` | Position is converted to a start offset by subtracting one; zero is rejected |
| `--ref -` | Empty reference allele: pure insertion at a boundary before the base at the normalized start |
| `--alt -` | Empty alternate allele: pure deletion of the matching reference interval |
| Both alleles one base | Single-base substitution, including an identity substitution |
| `--strand +` / `-` | Output orientation only; the edit and reference allele always refer to the original forward sequence |

The internal reference interval is half-open `[start, start + reference_length)`. Pure insertions can use boundaries `0..n` in zero-based mode, or `1..n+1` in one-based mode. A one-based insertion at position `p` occurs **before** forward base `p`; position `n+1` appends. These are explicit local edit coordinates, **not VCF-anchored insertion coordinates or HGVS syntax**.

Reference mismatch, invalid symbols, overflow, out-of-range intervals, repeated/unknown CLI options, and unsupported complex replacements return exit code 2 and a machine-readable error on stderr. Successful results are JSON on stdout. Full-sequence deletion is permitted and produces an empty output sequence. Input sequence and output size limits apply to the native library; the operating system can impose a smaller per-argument limit on this CLI.

Only one edit is supported. A dash is the CLI sentinel for an empty allele; an empty argument is rejected. Multibase replacement, anchored VCF indels, multiple overlapping edits, ambiguous bases, structural variants, contig assembly selection, transcript coordinates, phasing, and FASTA/VCF file parsing are deliberately unsupported.

## Why this project

Deep Genomics describes reproducibility, correctness, orthogonal assay validation, and model evaluation as platform priorities. Its BigRNA publication spans several RNA mechanisms. That makes deterministic input transformation an appropriate independent engineering experiment; it is **not evidence of a defect in Deep Genomics software**.

SpliceAI and other systems already perform RNA-related predictive tasks. Coordinate Guard does not compete with their predictive models. It isolates a prerequisite that can otherwise create convincing but mislocated model inputs. The negative baseline demonstrates an especially subtle case: an off-by-one shift can still pass a reference-allele check in repeated sequence.

```text
One-based edit on AAAA: position 2, A -> C
Correct normalized position: 1, result ACAA
Buggy unconverted position: 2, result AACA
```

This is notation for two test strings, not a biological result.

## Architecture

- `include/coordinate_guard.hpp`: a small typed edit/result interface with structured errors.
- `src/coordinate_guard.cpp`: native validation, bounds-safe edit application, and reverse complement.
- `src/main.cpp`: strict CLI parsing and JSON result/error serialization.
- `tests/test_guard.py`: independent Python string oracle, authored cases, and seeded metamorphic checks against the compiled executable.
- `examples/edits.json`: three readable synthetic examples with expected outputs.

C++ is used for the actual transformation core. Python is the independent verification harness, not the implementation of the core. There is no model inference in this milestone, so the project does not establish any inference speed advantage from C++.

The result includes the normalized forward interval, original/output lengths, edit kind, reference-check status, and output orientation. For an insertion, reference checking is explicitly `not_applicable_insertion`; an empty reference is not presented as evidence that an allele matched. The interval remains in the original forward coordinate space even when output is reverse-complemented.

## Verification evidence

The recorded verification passed **14 tests**, comprising **415 native CLI invocations**, including parser rejection cases. Every test launch uses the same counting helper. The environment, seeds, and measured suite runtime are in [benchmarks/local-verification.json](benchmarks/local-verification.json).

Meaningful checks include:

- Independent Python oracle agreement and zero/one-based equivalence over seeded sequence edits.
- Equivalent edits on reverse-complemented references for substitutions, insertions, and deletions.
- Reverse complement applied twice returns the original sequence.
- Start/end boundaries, append/prepend insertions, deletion of all bases, and reference mismatch rejection.
- Numeric overflow and malformed inputs.
- A known off-by-one negative baseline that produces a different output despite matching a repeated reference base.
- Forward-coordinate provenance retained for reverse-oriented outputs.

The timing includes subprocess startup and test-harness overhead. It is a reproducible correctness-suite measurement, **not a native throughput benchmark**. No biological accuracy, model quality, patient outcome, or performance comparison is inferred from it.

## Next milestones

1. Specify versioned assembly/contig metadata and file-based FASTA input before supporting larger sequences.
2. Add a narrowly declared VCF normalization adapter with its own reference fixtures and conformance tests, rather than silently treating this CLI as VCF-compatible.
3. Extend to batched edits and independently profile the native core after output equivalence is established.
4. Add a licensed open-model adapter only when its model inputs, output semantics, and evaluation data are independently specified. Public ClinVar labels are not direct functional RNA-effect ground truth.

## Research sources

Consulted 2026-10-31:

- [Deep Genomics BioFM platform](https://www.deepgenomics.com/biofm-platform): reproducibility, engineering correctness, evaluation, and lab-in-the-loop validation context.
- [BigRNA primary preprint](https://www.biorxiv.org/content/10.1101/2023.09.20.558508v1): existing RNA-model capabilities, not an accessible model dependency of this project.
- [Illumina SpliceAI](https://github.com/Illumina/SpliceAI): existing prediction implementation and prior-art distinction.
- [NCBI ClinVar downloads](https://www.ncbi.nlm.nih.gov/clinvar/docs/downloads/): possible future public metadata input; no ClinVar records are bundled or used in current test results.

## Boundaries

This project validates the stated sequence-edit contract on test inputs. It cannot establish the correctness of an unknown reference assembly, a variant annotation, a predictive model, or a biological interpretation. It is not medical software and accepts no real patient data in its supplied workflow. No deployment or external service call is performed.
