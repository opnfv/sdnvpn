===============================================================================
OPNFV Release Note for the Colorado.1.0 release of OPNFV for SDN VPN feature
===============================================================================

License
=======

This work is licensed under a Creative Commons Attribution 4.0 International
License. .. http://creativecommons.org/licenses/by/4.0 ..
(c) Tim Irnich (Ericsson) and others

Abstract
========

This document comprises the release notes for the SDN VPN feature contained in the Colorado
release of OPNFV.

Important notes
===============

In the Colorado release, SDN VPN only supports ODL as a backend. Make sure to always deploy
SDN VPN and ODL together. Make use of deployment scenarios including the SDNVPN feature.

Summary
=======

SDN VPN adds the possibility to create and associate BGP/MPLS based Virtual Private Networks (VPNs)
through the OpenStack Neutron BGPVPN API extension.

Release Data
============

+--------------------------------------+--------------------------------------+
| **Project**                          | sdnvpn                               |
|                                      |                                      |
+--------------------------------------+--------------------------------------+
| **Repo/tag**                         | Colorado.1.0                         |
|                                      |                                      |
+--------------------------------------+--------------------------------------+
| **Release designation**              | Colorado 1.0 follow-up release       |
|                                      |                                      |
+--------------------------------------+--------------------------------------+
| **Release date**                     | September 22 2016                    |
|                                      |                                      |
+--------------------------------------+--------------------------------------+
| **Purpose of the delivery**          | Including BGP stack - Quagga         |
|                                      | Fuel 9.0 baseline + Bug-fixes        |
|                                      | HEAT integration                     |
|                                      | 2 new e2e testcases for Functest     |
|                                      | Documentation                        |
|                                      |                                      |
+--------------------------------------+--------------------------------------+

Version change
--------------

Compared to the Brahmaputra release, a new version of ODL including several critical
bugfixes is deployed. Together with the new BGP stack and HEAT integration the user
can use now full stack bgp. New testcases to functest were added to guarantee
functionality.

Module version changes
~~~~~~~~~~~~~~~~~~~~~~
ODL has been upgraded to Beryllium SR3.

Document changes
~~~~~~~~~~~~~~~~
The amount documentation is increased substantially. E2E deployment docu and examples to use bgpvpn
is added.

Reason for version
------------------

Feature additions
~~~~~~~~~~~~~~~~~

SDN VPN adds the possibility to create and associate BGP/MPLS based Virtual Private Networks (VPNs)
through the OpenStack Neutron BGPVPN API extension.


Bug corrections
~~~~~~~~~~~~~~~

Several bugs in ODL VPN Service have been fixed in this release.

Deliverables
------------

Software deliverables
~~~~~~~~~~~~~~~~~~~~~

- Fuel plugin for OpenStack BGPVPN
- Changes to ODL Fuel plugin to activate VPN Service Karaf feature
- Integration of VPN Service functional tests and BGPVPN API tests into Functest framework

Documentation deliverables
~~~~~~~~~~~~~~~~~~~~~~~~~~

- Paragraph on SDN VPN feature for platform overview

- Configuration guide

- User guide

- Release noes (this document)

Known Limitations, Issues and Workarounds
=========================================

System Limitations
------------------

Floating ip will come with the Boron release so yardstick testcases cannot be run
and the user is only able to access the node through tenat network. Boron is targeted
for Colorado 2.0.
Due to lacking support for floating IPs in ODL VPNService (which replaces Netvirt as
Neutron backend in the SDN VPN scenarios), the following test suites have some restrictions
and are not executed:
- Tempest:
 tempest.api.compute.servers.test_create_server.ServersTestJSON
 tempest.api.compute.servers.test_create_server.ServersTestManualDisk
 tempest.api.compute.servers.test_server_actions.ServerActionsTestJSON
 tempest.scenario.test_network_basic_ops.TestNetworkBasicOps.test_network_basic_ops
 tempest.scenario.test_server_basic_ops.TestServerBasicOps.test_server_basic_ops
 tempest.scenario.test_volume_boot_pattern.TestVolumeBootPattern.test_volume_boot_pattern
 tempest.scenario.test_volume_boot_pattern.TestVolumeBootPatternV2.test_volume_boot_pattern

Yardstick uses the floating ip mechanism to connect to the instances using SSH.
Therefore, the default test cases have been replaced by the ones running tests on the
bare-metal servers. Feature specific Yardstick test cases have not been implemented,
we plan to add these in Colorado 2.0.

It is known that the performance of management operations is quite low. To work around
the overall timeout of functest, the performance tool Rally was excluded from the
test list. For Colorado 2.0 a much higher performance is expected and Rally it is
expected to be included again.


Known issues
------------

Workarounds
-----------

Test results
============

The deployment scenarios have successfully deployed in OPNFV CI many times and all Functest tests
(general and feature specific) are passing.

References
==========
