.. _-os-odl-bgpvpn-noha:

.. _-os-odl-bgpvpn-ha:

.. This work is licensed under a Creative Commons Attribution 4.0 International License.
.. SPDX-License-Identifier: CC-BY-4.0
.. (c) Periyasamy Palanisamy <periyasamy.palanisamy@ericsson.com> and others

=====================
SDN VPN Release Notes
=====================


Abstract
========

This document comprises the release notes for the SDN VPN feature contained in the Gambia
release of OPNFV.

Important notes
===============

In the Gambia release, SDN VPN only supports ODL as a backend. Make sure to always deploy
SDN VPN and ODL together. Make use of deployment scenarios including the SDNVPN feature such
as os_odl_bgpvpn_{ha|noha}.

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
| **Repo/tag**                         | opnfv-7.0.0                               |
|                                      |                                           |
+--------------------------------------+-------------------------------------------+
| **Release designation**              | Gambia 7.0                                |
|                                      |                                           |
+--------------------------------------+-------------------------------------------+
| **Release date**                     | Jan 01 2019                               |
|                                      |                                           |
+--------------------------------------+-------------------------------------------+
| **Purpose of the delivery**          | New test cases                            |
|                                      |                                           |
+--------------------------------------+-------------------------------------------+

Version change
--------------

Compared to the Fraser release, functest testcases were enriched to guarantee functionality.
Also several enhancements were added to improve testing efficiency.

Module version changes
~~~~~~~~~~~~~~~~~~~~~~
.. ODL has been upgraded to Nitrogen.

Document changes
~~~~~~~~~~~~~~~~

Reason for version
------------------

Feature additions
~~~~~~~~~~~~~~~~~

SDN VPN adds the possibility to create and associate BGP/MPLS based
Virtual Private Networks (VPNs) through the OpenStack Neutron BGPVPN
API extension.

There has been no functional scope change in the Fraser release, the
main deliverable is newer upstream versions and additional test
coverage.


Bug corrections
~~~~~~~~~~~~~~~

- Several bugs in ODL VPN Service have been fixed in this release.

Deliverables
------------

Software deliverables
~~~~~~~~~~~~~~~~~~~~~

- Orchestrate BGPVPN with Openstack HEAT templates
- Verify BGP route exchange with a peer in both directions
- Support for ECMP load balancing
- Consolidate image creation in Apex and Fuel
- Remove the dependency between not running quagga and created flows
- Delete ODL configuration after each test case run
- Add BGPVPN scenarios to XCI and enable SDNVPN tests
- Enable and test ODL clustering for bgpvpn-ha scenario


Documentation deliverables
~~~~~~~~~~~~~~~~~~~~~~~~~~

- Installation guide
- Release notes (this document)
- Overview
- Test scenario description

Known Limitations, Issues and Workarounds
=========================================


System Limitations
------------------

Known issues
------------

Moving to the new NetVirt has caused a regression in which a subnet
cannot be both attached to a Router and Network associated to a VPN.
This has been worked around in the tests and the upstream bug is being
tracked [0]_ and [2]_.

NAT for a VM which is in a private neutron network does not work. Instances
created in subnets that are connected to the public network via a gateway
should have external connectivity. This does not work and can be worked
around by assigning a Floating IP to the instance [1]_.

Currently we observe non-deterministic failures of individual tests within the
SDNVPN section of the Functest suite, which are not reproducible in the development
environment. In a development environment all Functest tests are successful.
Sporadic failures have been observed in test cases 4 and 8. Furthermore, the
check of bgpd service running on Controller node, in test case 3, has a constant
failure trend for Apex environment.

Workarounds
-----------

The router/network association mutual exclusivity is worked around
by not network associating subnets attached to routers.

The NAT issues are worked around by assigning floating IPs to VMs that require
external connectivity.

Test results
============

The deployment scenarios have successfully deployed in OPNFV CI many
times and all Functest tests (general and feature specific) are passing,
with the exceptions described above.

References
==========
.. [0] https://jira.opnfv.org/projects/SDNVPN/issues/SDNVPN-94
.. [1] https://jira.opnfv.org/projects/SDNVPN/issues/SDNVPN-99
.. [2] https://jira.opendaylight.org/browse/NETVIRT-932