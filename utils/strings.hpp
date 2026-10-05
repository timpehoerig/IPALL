#ifndef STRINGS
#define STRINGS

#include <string>
#include "types.hpp"

std::string to_string(ivec model, bool neg = false);
std::string to_string(ivvec model, bool neg = false);
std::string to_string(const ivec &decisions, const ivec &reason_to_dl, int dl, int decision_to_propagate, bool propagate_lit, bool debug = false);

#endif
