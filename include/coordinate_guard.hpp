#pragma once
#include <cstddef>
#include <stdexcept>
#include <string>

namespace coordinate_guard {
struct Error : std::runtime_error {
    std::string code;
    Error(std::string code, std::string message);
};
struct Edit {
    std::size_t position;
    bool one_based;
    std::string reference;
    std::string alternate;
    char output_strand;
};
struct Result {
    std::size_t start;
    std::size_t end;
    std::size_t original_length;
    std::string kind;
    std::string reference_check;
    std::string sequence;
};
std::string reverse_complement(const std::string& sequence);
Result apply(const std::string& forward_sequence, const Edit& edit);
}
