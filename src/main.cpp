#include "coordinate_guard.hpp"
#include <charconv>
#include <iostream>
#include <map>
#include <string>
#include <system_error>

namespace {
std::size_t position(const std::string& value) {
    if (value.empty() || value.find_first_not_of("0123456789") != std::string::npos)
        throw coordinate_guard::Error("invalid_position", "Position must be an unsigned decimal integer");
    std::size_t result = 0;
    auto parsed = std::from_chars(value.data(), value.data() + value.size(), result);
    if (parsed.ec != std::errc{} || parsed.ptr != value.data() + value.size())
        throw coordinate_guard::Error("invalid_position", "Position exceeds supported integer range");
    return result;
}
}
int main(int argc, char** argv) {
    try {
        if (argc == 2 && std::string(argv[1]) == "--help") {
            std::cout << "coordinate-guard --sequence ACGT --position 2 --coordinates one --ref C --alt T --strand +\n"
                         "Use --ref - for a pure insertion; --alt - for a pure deletion.\n"
                         "All edits refer to the forward sequence; strand changes output orientation only.\n";
            return 0;
        }
        std::map<std::string, std::string> args;
        const std::map<std::string, bool> allowed = {{"--sequence",true},{"--position",true},{"--coordinates",true},{"--ref",true},{"--alt",true},{"--strand",true}};
        if ((argc - 1) % 2) throw coordinate_guard::Error("invalid_arguments", "Every option requires one value");
        for (int i = 1; i < argc; i += 2) {
            std::string key = argv[i];
            if (!allowed.count(key) || args.count(key)) throw coordinate_guard::Error("invalid_arguments", "Unknown or repeated option");
            args.emplace(key, argv[i+1]);
        }
        if (args.size() != allowed.size()) throw coordinate_guard::Error("invalid_arguments", "All six options are required");
        if (args.at("--coordinates") != "zero" && args.at("--coordinates") != "one")
            throw coordinate_guard::Error("invalid_coordinates", "Coordinates must be zero or one");
        if (args.at("--strand") != "+" && args.at("--strand") != "-")
            throw coordinate_guard::Error("invalid_strand", "Output strand must be + or -");
        if (args.at("--ref").empty() || args.at("--alt").empty())
            throw coordinate_guard::Error("invalid_allele", "Use the dash sentinel for an empty allele");
        const auto input_position = position(args.at("--position"));
        const auto ref = args.at("--ref") == "-" ? "" : args.at("--ref");
        const auto alt = args.at("--alt") == "-" ? "" : args.at("--alt");
        const coordinate_guard::Edit edit{input_position, args.at("--coordinates") == "one", ref, alt, args.at("--strand")[0]};
        const auto result = coordinate_guard::apply(args.at("--sequence"), edit);
        std::cout << "{\"schema_version\":1,\"status\":\"ok\",\"coordinate_system\":\"" << args.at("--coordinates")
                  << "\",\"input_position\":" << input_position << ",\"forward_interval\":[" << result.start << ',' << result.end
                  << "],\"kind\":\"" << result.kind << "\",\"reference_check\":\"" << result.reference_check
                  << "\",\"output_strand\":\"" << edit.output_strand << "\",\"original_length\":" << result.original_length
                  << ",\"output_length\":" << result.sequence.size() << ",\"sequence\":\"" << result.sequence << "\"}\n";
        return 0;
    } catch (const coordinate_guard::Error& error) {
        // Messages are fixed internal strings, not unescaped user input.
        std::cerr << "{\"status\":\"error\",\"code\":\"" << error.code << "\",\"message\":\"" << error.what() << "\"}\n";
        return 2;
    } catch (const std::exception&) {
        std::cerr << "{\"status\":\"error\",\"code\":\"internal_error\"}\n";
        return 3;
    }
}
