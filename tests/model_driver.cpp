#include "adapters/fixture.hpp"
#include "core/support.hpp"
#include "db/query.hpp"
#include "package/candidate.hpp"
#include "package/manifest.hpp"
#include <iostream>
#include <string>
#include <type_traits>

int main(int argc, char** argv) {
    if (argc != 2) {
        return 2;
    }
    static_assert(!std::is_constructible_v<aslice::package::Manifest, aslice::core::Json>);
    static_assert(!std::is_copy_constructible_v<aslice::db::Snapshot>);
    const auto fail = [](const char* message) {
        std::cerr << message << '\n';
        return 1;
    };
    if (aslice::package::Target::create("13", "v1") ||
        aslice::package::Target::create("10.11", "v4")) {
        return fail("invalid target accepted");
    }
    if (aslice::package::Manifest::parse(aslice::core::Json::object()) ||
        aslice::adapters::fixture::Package::parse(nullptr)) {
        return fail("invalid document accepted");
    }
    if (aslice::core::parse_json("{") || aslice::core::parse_json("{\"a\":1,\"a\":2}") ||
        aslice::core::read_bytes(std::string(argv[1]) + ".missing")) {
        return fail("JSON or filesystem failure escaped its result boundary");
    }
    const auto snapshot = aslice::db::Snapshot::create({}, {"client-state", "", ""});
    if (snapshot || snapshot.error().code != "snapshot_limit") {
        return fail("snapshot error escaped its boundary");
    }
    const auto bytes = aslice::core::take(aslice::core::read_bytes(argv[1]));
    const auto document = aslice::core::take(aslice::core::parse_json(bytes));
    auto generation = aslice::adapters::fixture::Generation::parse(document, "2");
    if (!generation) {
        return fail("legacy generation refused");
    }
    const auto serialized =
        aslice::adapters::fixture::generation_document(generation->id(), generation->parent(),
                                                       generation->selected(), generation->roots())
            .dump();
    if (serialized != bytes) {
        return fail("legacy generation bytes changed");
    }
    const auto& selected = generation->selected();
    if (selected.at("core:hello").candidate().artifact() !=
            "7a444a767dd64a52ea9b485314f5b7f7c234f13ad303de53a5e29dfe20c6a4f5" ||
        selected.at("core:greeting").candidate().artifact() !=
            "8549ef5f09cbfd82affd5d5a0a10bf931ea1199e9c4892811fcb4fa6da5f186c") {
        return fail("legacy fixture identities changed");
    }
    auto corrupt = document;
    corrupt["selected"]["core:hello"]["version"] = "not-a-version";
    if (aslice::adapters::fixture::Generation::parse(corrupt, "2") ||
        aslice::adapters::fixture::Generation::parse(document, "3")) {
        return fail("invalid generation accepted");
    }
    return 0;
}
