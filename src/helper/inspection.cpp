#include "helper/inspection.hpp"
#include "core/result.hpp"
#include "core/support.hpp"
#include "helper/protocol.hpp"
#include "package/manifest.hpp"
#include <string>

namespace aslice::helper {
core::Result<core::Json> inspect_message(const core::Json& request,
                                         const std::string& authenticated_caller) {
    return core::capture([&] {
        const auto& binding = request.at("binding");
        // Only correlation identifiers come from the bootstrap message. Caller,
        // role, capabilities and digest are independently established here.
        Grant grant{authenticated_caller,
                    "extract",
                    binding.at("instance_id").get<std::string>(),
                    binding.at("operation_id").get<std::string>(),
                    binding.at("session_id").get<std::string>(),
                    "sha256:" + core::take(core::digest(request.at("arguments").dump())),
                    {"manifest.inspect"}};
        Session session{grant};
        return core::take(session.execute(request, [](const Request& admitted, Outcome& outcome) {
            outcome.observations.push_back(
                core::take(package::Manifest::parse(admitted.arguments)).inspect());
        }));
    });
}
} // namespace aslice::helper
