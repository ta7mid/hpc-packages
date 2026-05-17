#include <ns3/core-module.h>
#include <ns3/network-module.h>

#include <iostream>

int main()
{
    // Touch a real ns-3 type and a real ns-3 function so the linker must
    // resolve them. ns3::Simulator::Stop is enough to exercise the link
    // against ns3::core; we don't actually run any events.
    ns3::Time t = ns3::Seconds(1.0);
    (void)t;
    ns3::Simulator::Stop();

    std::cout << "ns-3 test_package OK: version "
              << NS3_VERSION_MAJOR << "." << NS3_VERSION_MINOR
              << "\n";
    return 0;
}
