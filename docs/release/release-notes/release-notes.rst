==========================================================================
Release Note for the Danube.3.0 release of OPNFV for SDN VPN feature
==========================================================================

License
=======

This work is licensed under a Creative Commons Attribution 4.0 International
License. .. http://creativecommons.org/licenses/by/4.0 ..
(c) Tim Irnich (Ericsson) and others

Abstract
========

This document comprises the release notes for the SDN VPN feature contained in the Danube
release of OPNFV.

Important notes
===============

In the Danube release, SDN VPN only supports ODL as a backend. Make sure to always deploy
SDN VPN and ODL together. Make use of deployment scenarios including the SDNVPN feature.

Summary
=======

SDN VPN adds the possibility to create and associate BGP/MPLS based Virtual Private Networks (VPNs)
through the OpenStack Neutron BGPVPN API extension.

Release Data
============

+--------------------------------------+-------------------------------------------+
| **Project**                          | sdnvpn                                    |
|                                      |                                           |
+--------------------------------------+-------------------------------------------+
| **Repo/tag**                         | Danube.3.0                                |
|                                      |                                           |
+--------------------------------------+-------------------------------------------+
| **Release designation**              | Danube 3.0 follow-up release              |
|                                      |                                           |
+--------------------------------------+-------------------------------------------+
| **Release date**                     | June 23 2017                              |
|                                      |                                           |
+--------------------------------------+-------------------------------------------+
| **Purpose of the delivery**          | Including BGP stack - 6WIND Zrpcd/Quagga  |
|                                      | Fuel 10.0 baseline + bug fixes            |
|                                      | Deployment with Apex                      |
|                                      | Integration with Boron SR2.0 and bugfixes |
|                                      | 4 new e2e testcases for Functest          |
|                                      | Horizon integration for networking-bgpvpn |
|                                      |                                           |
+--------------------------------------+-------------------------------------------+

Version change
--------------

Compared to the Colorado release, a new version of ODL including
several critical bugfixes is deployed. Together with the new BGP
stack, integration with Apex, the Horizon dashboards and bugfixes the
user has even more features available. New testcases were added to
functest to guarantee functionality.

Module version changes
~~~~~~~~~~~~~~~~~~~~~~
ODL has been upgraded to Boron SR4.

Document changes
~~~~~~~~~~~~~~~~

Reason for version
------------------

Feature additions
~~~~~~~~~~~~~~~~~

SDN VPN adds the possibility to create and associate BGP/MPLS based
Virtual Private Networks (VPNs) through the OpenStack Neutron BGPVPN
API extension.

A new installer based on Apex is provided.

The Horizon dashboard for the OpenStack Neutron BGPVPN API extensions
is available.

Bug corrections
~~~~~~~~~~~~~~~

- Several bugs in ODL VPN Service have been fixed in this release.

- Floating IP is now working and tested in functest, relevant Tempest
  tests have been enabled.

- Performance issues have been rectified and the relevant tests have
  been enabled again.

- Yardstick testcases have been enabled again.

Deliverables
------------

Software deliverables
~~~~~~~~~~~~~~~~~~~~~

- Fuel plugin for OpenStack BGPVPN
- Changes to ODL Fuel plugin to activate the NetVirt Karaf features
  and to apply the appropriate configuration. Also changes to
  implement integration with 6Wind Zrpcd and Quagga.
- Changes to Apex to enable a BGPVPN deployment.
- Integration of VPN Service functional tests and BGPVPN API tests into Functest framework.
- Enabling performance tests in Yardstick.
- Changes to 6Wind Zrpcd to enable integration with Apex.

Documentation deliverables
~~~~~~~~~~~~~~~~~~~~~~~~~~

- Paragraph on SDN VPN feature for platform overview

- Configuration guide

- User guide

- Release notes (this document)

Known Limitations, Issues and Workarounds
=========================================


System Limitations
------------------

Known issues
------------

Moving to the new NetVirt has caused a regression in which a subnet
cannot be both attached to a Router and Network associated to a VPN.
This has been worked around in the tests and the upstream bug is being
tracked [0].

NAT for a VM which is in a private neutron network does not work. Instances
created in subnets that are connected to the public network via a gateway
should have external connectivity. This does not work and can be worked
around by assigning a Floating IP to the instance [1].

Currently we observe non-deterministic failures of individual tests within the
SDNVPN section of the Functest suite, which are not reproducible in the development
environment. In a development environment all Functest tests are successful.
Sporadic failures have been observed in test cases 1,4 and 8. Furthermore, the
check of bgpd service running on Controller node, in test case 3, has a constant
failure trend for Apex environment. Also for Apex environment we observe constant
failure in refstack, during the server action test_reboot_server_hard [2].

Workarounds
-----------

The router/network association mutual exclusivity is worked around
by not network associating subnets attached to routers.

The NAT issues are worked around by assigning floating IPs to VMs that require
external connectivity.

For the failures observed in CI, no workaround is required since the faults were
not reproducible in live deployments.[3]

Test results
============

The deployment scenarios have successfully deployed in OPNFV CI many
times and all Functest tests (general and feature specific) are passing,
with the exceptions described above.

References
==========
[0] https://jira.opnfv.org/projects/SDNVPN/issues/SDNVPN-94
[1] https://jira.opnfv.org/projects/SDNVPN/issues/SDNVPN-99
[2] https://jira.opnfv.org/projects/SDNVPN/issues/SDNVPN-172
[3] https://jira.opnfv.org/projects/SDNVPN/issues/SDNVPN-170
