#include "../../cadical/src/cadical.hpp"

#include "../utils/argparser.hpp"
#include "../utils/strings.hpp"
#include "../utils/parser.hpp"
#include "../utils/types.hpp"

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <algorithm>
#include <unordered_set>
#include <cassert>
#include <charconv>
#include <cmath>
#include <cstdint>


// global meta variables
bool COUNT = false;
bool VERBOSE = false;
bool HELP = false;

uint64_t count = 0;

// cnf must be global so EnumProp can use it
tcnf cnf;

// paths
const char* NEGATED_MODELS = "tmp_cadicall_negated_models.txt";


void write_models(const char* name, tmodels models) {
    std::ofstream file(NEGATED_MODELS);
    char buffer[32];

    std::size_t counter = 1;

    for (const auto& model : models) {
        if (model.empty()) continue;

        // Write prefix: "i <counter> "
        file.put('i');
        file.put(' ');
        auto [cptr, cec] = std::to_chars(buffer, buffer + 32, counter++);
        file.write(buffer, cptr - buffer);
        file.put(' ');

        // Write first literal
        auto [ptr, ec] = std::to_chars(buffer, buffer + 32, -model[0]);
        file.write(buffer, ptr - buffer);

        // Write remaining literals
        for (size_t i = 1; i < model.size(); i++) {
            file.put(' ');
            auto [ptr2, ec2] = std::to_chars(buffer, buffer + 32, -model[i]);
            file.write(buffer, ptr2 - buffer);
        }

        file.put(' ');
        file.put('0');
        file.put('\n');
    }
}


class EnumProp : public CaDiCaL::ExternalPropagator {

    private:
        // decision level
        size_t dl = 0;

        // decisions == [0, d1@1, d2@2, ...]
        // dl == |decisions|
        ivec decisions;
        ivec reason_to_dl;

        bool propagate_lit = false;
        int decision_to_propagate;


    public:

        void init(int n) {
            decisions.reserve(n + 1);
            decisions.push_back(0);

            reason_to_dl.assign(n + 1, -1);
        }


        CaDiCaL::Solver *solver;
        CaDiCaL::Internal *internal;

        tmodels all_models;

        bool cb_check_found_model (const tmodel &model) override {
            if (VERBOSE) std::cout << "c\nc cb_check_found_model:" << to_string(model) << std::endl;

            if (COUNT) {
                count++;
                if (VERBOSE) std::cout << "c count += 1" << std::endl;
            } else {
                all_models.push_back(model);
            }

            if (dl <= 0) {
                if (VERBOSE) std::cout << "c no more decisions to flip, terminating" << std::endl;
                solver->terminate();
                return false;
            }

            solver->force_backtrack(dl - 1);

            if (VERBOSE) std::cout << to_string(decisions, reason_to_dl, dl) << std::endl;

            return false;
        };

        // always false as we DO NOT want to add clauses
        bool cb_has_external_clause (bool &is_forgettable) override {
            if (VERBOSE) std::cout << "c\nc cb_has_external_clause:" << std::endl;
            return false;
        };

        int cb_add_external_clause_lit () override {
            if (VERBOSE) std::cout << "c\nc cb_add_external_clause_lit:" << std::endl;
            return 0;
        };

        // this function is called when observed variables are assigned (either by BCP, Decide, or Learning a unit clause). It has a single read-only argument containing literals that became satisfied by the new assignment. In case the notification reports more than one literal, it is guaranteed that all of the reported literals were assigned on the same (current) decision level.
        void notify_assignment(const ivec &list) override {
            if (VERBOSE) std::cout << "c\nc notify_assignment: " << to_string(list) << std::endl;

            assert (list.size() > 0);

            if (solver->is_decision(list[0])) {
                if (decisions.size() <= dl) {
                    decisions.push_back(list[0]);
                } else {
                    decisions[dl] = list[0];
                }
            }

            if (VERBOSE) {
                std::cout << "c decided: " + std::to_string(decisions[dl]) + "@" + std::to_string(dl) << std::endl;
                std::cout << to_string(decisions, reason_to_dl, dl) << std::endl;
            }
        };

        // the call of this function indicates to the user that on the trail a new decision level has started. The function does not report the actual decision that started this new level or the current decision level — it only reports that a decision happened and thus, the decision level is increased.
        void notify_new_decision_level () override {
            if (VERBOSE) std::cout << "c\nc notify_new_decision_level: " << std::to_string(dl + 1) << std::endl;

            dl++;

            if (VERBOSE) std::cout << to_string(decisions, reason_to_dl, dl) << std::endl;
        };

        // this function indicates that the solver backtracked to a lower decision level. Its single argument reports the new decision level. All assignments that were made above this target decision level must be considered as unassigned.
        void notify_backtrack (size_t new_level) override {
            if (VERBOSE) std::cout << "c\nc notify_backtrack: " << std::to_string(new_level) << std::endl;

            while (decisions.size() - 1 > new_level) {
                if (VERBOSE) std::cout << "c removed decision: " << std::to_string(decisions.back()) << std::endl;

                decision_to_propagate = decisions.back();
                decisions.pop_back();
                propagate_lit = true;
            }

            dl = new_level;

            if (VERBOSE) std::cout << to_string(decisions, reason_to_dl, dl) << std::endl;
        };

        // called before the solver makes a decision. Return your decision or 0 (solver makes one).
        int cb_decide () override {
            if (VERBOSE) std::cout << "c\nc cb_decide: 0 (let the solver decide)" << std::endl;

            return 0;
        };

        int cb_propagate () override {
            if (VERBOSE) std::cout << "c\nc cb_propagate:" << std::endl;

            if (!propagate_lit) {
                return 0;
            }

            propagate_lit = false;
            reason_to_dl[std::abs(decision_to_propagate)] = dl;
            if (VERBOSE) std::cout << "c propagated: " << std::to_string(-decision_to_propagate) << " @ " << std::to_string(dl) << std::endl;


            if (VERBOSE) std::cout << to_string(decisions, reason_to_dl, dl) << std::endl;

            return -decision_to_propagate;
        };

        int cb_add_reason_clause_lit (int propagated_lit) override {
            if (VERBOSE) std::cout << "c\nc cb_add_reason_clause_lit: " << std::to_string(propagated_lit) << std::endl;

            static bool flag = true;
            static size_t reason_clause_idx = 0;

            if (flag) {
                reason_clause_idx = reason_to_dl[std::abs(propagated_lit)];
                flag = false;
                if (VERBOSE) std::cout << "c adding: " << std::to_string(propagated_lit) << std::endl;

                return propagated_lit;
            }

            if (reason_clause_idx > 0) {
                if (VERBOSE) std::cout << "c adding: " << std::to_string(-decisions[reason_clause_idx]) << std::endl;

                return -decisions[reason_clause_idx--];
            }

            if (VERBOSE) std::cout << "c adding: 0" << std::endl;
            flag = true;
            if (VERBOSE) std::cout << to_string(decisions, reason_to_dl, dl) << std::endl;
            return 0;
        };
};


void arg_parser(int argc, char* argv[], bool& count, bool& verbose, bool& help) {
    std::map<std::string, std::string> parsedArgs = parseArgs(argc, argv);
    count = parsedArgs.count("count") || parsedArgs.count("c");
    verbose = parsedArgs.count("verbose") || parsedArgs.count("v");
    help = parsedArgs.count("help") || parsedArgs.count("h");
}


int main(int argc, char* argv[]) {
    // arg parser
    arg_parser(argc, argv, COUNT, VERBOSE, HELP);

    if (HELP) {
        std::string msg =
            "\n\n"
            "Welcome to CaDiCAll a model enumerator using IPASIR-UP without Blocking Clauses\n"
            "\n"
            "USAGE:\n"
            "\tcadicall [--Option (-o)] <path to cnf>\n"
            "\n"
            "OPTIONS:\n"
            "\n"
            "\t-h --help \t Show this menu\n"
            "\t-c --count \t Returns number of models (does not store the models - no exp memory usage)\n"
            "\t-v --verbose \t Returns the log and all models\n";
        std::cout << msg;
        return 0;
    }

    std::cout << "c Runnning the solver with the following options:" << std::endl;
    if (COUNT) std::cout << "c \tCOUNT" << std::endl;
    if (VERBOSE) std::cout << "c \tVERBOSE" << std::endl;

    // create a new solver instance
    CaDiCaL::Solver *solver = new CaDiCaL::Solver;

    // setting options for chronological backtracking
    // how to disable preprocessing?
    // false != not set
    // solver->set("chrono", true);
    solver->set("chronoalways", true);
    solver->set("chronostrict", true);
    solver->set("restart", false);
    solver->set("inprocessing", false);
    solver->set("rephase", true);
    solver->set("log", false);

    // create a new EnumProp instance
    EnumProp *ep = new EnumProp;

    ep->solver = solver;

    // connect EnumProp to solver instance
    solver->connect_external_propagator(ep);

    ep->are_reasons_forgettable = true;

    // extract num of variables from dimacs file
    int numVariables = 0;

    solver->read_dimacs(argv[argc - 1], numVariables);

    // initialise all vectors
    ep->init(numVariables);

    // mark all variables as relevant for observing
    for (int var = 1; var <= numVariables; var++) {
        solver->add_observed_var(var);
    }

    // run solver
    if (VERBOSE) std::cout << "c start solving\nc" << std::endl;
    int res = solver->solve();

    if (VERBOSE) {
        std::cout << "c all models:\n" + to_string(ep->all_models) << std::endl;

        std::cout << res;
        std::cout << "" << std::endl;
    }

    if (COUNT) {
        std::cout << "NUMBER SATISFYING ASSIGNMENTS" << std::endl;
        std::cout << count;
        std::cout << "" << std::endl;
    }

    // write negated models to file
    write_models(NEGATED_MODELS, ep->all_models);

    // disconnect EnumProp
    solver->disconnect_external_propagator();

    // delete the solver instance
    delete solver;

    return 0;
}
