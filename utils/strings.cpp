#include <vector>
#include <string>
#include <charconv>
#include "strings.hpp"


// to_string(model) == "x y -z"
std::string to_string(ivec model, bool neg) {
    if (model.empty()) return "";

    std::string str;
    str.reserve(model.size() * 12);

    char buffer[32];

    int lit = model[0];
    if (neg) lit = -lit;
    auto [ptr, ec] = std::to_chars(buffer, buffer + 32, lit);
    str.append(buffer, ptr);

    for (size_t i = 1; i < model.size(); i++) {
        str.push_back(' ');
        int lit = model[i];
        if (neg) lit = -lit;
        auto [ptr, ec] = std::to_chars(buffer, buffer + 32, model[i]);
        str.append(buffer, ptr);
    }

    return str;
}


// to_string(models) == "model1 | model2"
std::string to_string(ivvec models, bool neg) {

    std::string str;

    for (ivec model : models) {
        str += "c " + to_string(model, neg) + "\n";
    }

    if (str.size() > 2 && str[str.size()-2] == '|') {
        str.resize(str.size()-2);
    }

    return str;
}


std::string to_string(const ivec &decisions, const ivec &reason_to_dl, int dl, int decision_to_propagate, bool propagate_lit, bool debug) {
    std::string out = "";
    if (debug) {
        out += "c debug decisions: " + to_string(decisions) + "\n";
        out += "c debug reason_to_dl: " + to_string(reason_to_dl) + "\n";
        out += "c debug dl: " + std::to_string(dl) + "\n";
        out += "c debug decision_to_propagate: " + std::to_string(decision_to_propagate) + "\n";
        out += "c debug propagate_lit: " + std::to_string(propagate_lit) + "\n";
    }

    out += "c decisions: ";
    for (int idl = 0; idl <= dl; idl++) {
        if (idl >= (int)decisions.size()) break;
        out += std::to_string(decisions[idl]) + "@" + std::to_string(idl) + " ";
    }
    return out;
}
