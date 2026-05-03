#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <cmath>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

namespace py = pybind11;

std::string normalize_text(const std::string& input, int max_len) {
    std::string out;
    out.reserve(input.size());

    bool prev_space = true;
    for (char ch : input) {
        unsigned char c = static_cast<unsigned char>(ch);
        bool is_space = (c == ' ' || c == '\n' || c == '\r' || c == '\t' || c == '\f' || c == '\v');
        if (is_space) {
            if (!prev_space) {
                out.push_back(' ');
                prev_space = true;
            }
        } else {
            out.push_back(ch);
            prev_space = false;
        }
        if (static_cast<int>(out.size()) >= max_len) {
            break;
        }
    }

    while (!out.empty() && out.back() == ' ') {
        out.pop_back();
    }
    return out;
}

std::unordered_map<std::string, double> rrf_fuse(
    const std::vector<std::string>& fts_ids,
    const std::vector<std::string>& semantic_ids,
    int k
) {
    std::unordered_map<std::string, int> rank_fts;
    std::unordered_map<std::string, int> rank_sem;

    for (size_t i = 0; i < fts_ids.size(); ++i) {
        if (!rank_fts.count(fts_ids[i])) {
            rank_fts[fts_ids[i]] = static_cast<int>(i) + 1;
        }
    }

    for (size_t i = 0; i < semantic_ids.size(); ++i) {
        if (!rank_sem.count(semantic_ids[i])) {
            rank_sem[semantic_ids[i]] = static_cast<int>(i) + 1;
        }
    }

    std::unordered_map<std::string, double> out;

    for (const auto& id : fts_ids) {
        if (!out.count(id)) out[id] = 0.0;
        auto it = rank_fts.find(id);
        if (it != rank_fts.end()) {
            out[id] += 1.0 / static_cast<double>(it->second + k);
        }
    }

    for (const auto& id : semantic_ids) {
        if (!out.count(id)) out[id] = 0.0;
        auto it = rank_sem.find(id);
        if (it != rank_sem.end()) {
            out[id] += 1.0 / static_cast<double>(it->second + k);
        }
    }

    return out;
}

PYBIND11_MODULE(memoryfeed_native, m) {
    m.doc() = "MemoryFeed native acceleration module";
    m.def("normalize_text", &normalize_text, py::arg("input"), py::arg("max_len") = 2000);
    m.def("rrf_fuse", &rrf_fuse, py::arg("fts_ids"), py::arg("semantic_ids"), py::arg("k") = 60);
}
