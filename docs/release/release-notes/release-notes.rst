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

This document comprises the release notes for the SDN VPN feature contained in the Euphrates
release of OPNFV.

Important notes
===============

In the Euphrates release, SDN VPN only supports ODL as a backend. Make sure to always deploy
SDN VPN and ODL together. Make use of deployment scenarios including the SDNVPN feature such as os_odl_bgpvpn_{ha|noha}.

Summary
=======

SDN VPN adds the possibility to create and associate BGP/MPLS based
Virtual Private Networks (VPNs) through the OpenStack Neutron BGPVPN API
extension. See the scenario description and the user guide for details.


Release Data
============

+--------------------------------------+-------------------------------------------+
| **Project**                          | sdnvpn                                    |
|                                      |                                           |
+--------------------------------------+-------------------------------------------+
| **Repo/tag**                         | Euhprates 1.0                             |
|                                      |                                           |
+--------------------------------------+-------------------------------------------+
| **Release designation**              | Euphrates 1.0 - initial release           |
|                                      |                                           |
+--------------------------------------+-------------------------------------------+
| **Release date**                     | Oct 20 2017                               |
|                                      |                                           |
+--------------------------------------+-------------------------------------------+
| **Purpose of the delivery**          | Rebased to new upstream versions          |
|                                      | Removed Fuel deployment scenario          |
|                                      | Couple of new test cases                  |
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
ODL has been upgraded to Carbon SR2.

Document changes
~~~~~~~~~~~~~~~~
The previous monolithic user guide, which was also covering install and
config, has been broken up into multiple documents.


Reason for version
------------------

Feature additions
~~~~~~~~~~~~~~~~~

SDN VPN adds the possibility to create and associate BGP/MPLS based
Virtual Private Networks (VPNs) through the OpenStack Neutron BGPVPN
API extension.

There has been no functional scope change in the Euphrates release, the
main deliverable is newer upstream versions and additional test
coverage.


Bug corrections
~~~~~~~~~~~~~~~

- Several bugs in ODL VPN Service have been fixed in this release.

Deliverables
------------

Software deliverables
~~~~~~~~~~~~~~~~~~~~~

- Changes to Apex to enable a BGPVPN deployment and integration of Quagga BGP.
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
