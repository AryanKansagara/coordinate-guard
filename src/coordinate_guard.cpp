#include "coordinate_guard.hpp"
#include <algorithm>
#include <utility>

namespace coordinate_guard {
Error::Error(std::string value, std::string message)
    : std::runtime_error(std::move(message)), code(std::move(value)) {}
namespace {
void validate_dna(const std::string& text) {
    if (std::any_of(text.begin(), text.end(), [](char base) {
            return base != 'A' && base != 'C' && base != 'G' && base != 'T';
        })) throw Error("invalid_dna", "Only uppercase A, C, G, T are supported");
}
}
std::string reverse_complement(const std::string& sequence) {
    validate_dna(sequence);
    std::string result;
    result.reserve(sequence.size());
    for (auto base = sequence.rbegin(); base != sequence.rend(); ++base) {
        switch (*base) {
            case 'A': result += 'T'; break;
            case 'T': result += 'A'; break;
            case 'C': result += 'G'; break;
            case 'G': result += 'C'; break;
        }
    }
    return result;
}
Result apply(const std::string& sequence, const Edit& edit) {
    if (sequence.empty()) throw Error("empty_sequence", "Input sequence must be nonempty");
    if (sequence.size() > 1000000) throw Error("sequence_too_large", "Input exceeds one million bases");
    validate_dna(sequence);
    validate_dna(edit.reference);
    validate_dna(edit.alternate);
    if (edit.output_strand != '+' && edit.output_strand != '-')
        throw Error("invalid_strand", "Output strand must be + or -");
    std::string kind;
    if (edit.reference.empty() && !edit.alternate.empty()) kind = "insertion";
    else if (!edit.reference.empty() && edit.alternate.empty()) kind = "deletion";
    else if (edit.reference.size() == 1 && edit.alternate.size() == 1) kind = "snv";
    else throw Error("unsupported_edit", "Only single-base substitutions, pure insertions and pure deletions are supported");
    if (edit.one_based && edit.position == 0)
        throw Error("invalid_position", "One-based positions start at one");
    const std::size_t start = edit.one_based ? edit.position - 1 : edit.position;
    // Subtract after checking start so addition cannot wrap before bounds validation.
    if (start > sequence.size() || edit.reference.size() > sequence.size() - start)
        throw Error("out_of_bounds", "Reference interval lies outside the sequence");
    const std::size_t end = start + edit.reference.size();
    if (sequence.compare(start, edit.reference.size(), edit.reference) != 0)
        throw Error("reference_mismatch", "Reference allele does not match the forward sequence");
    if (edit.alternate.size() > 1000000 || sequence.size() - edit.reference.size() > 1000000 - edit.alternate.size())
        throw Error("result_too_large", "Edited output exceeds one million bases");
    std::string modified = sequence.substr(0, start) + edit.alternate + sequence.substr(end);
    if (edit.output_strand == '-') modified = reverse_complement(modified);
    return {start, end, sequence.size(), kind,
            edit.reference.empty() ? "not_applicable_insertion" : "matched",
            std::move(modified)};
}
}
