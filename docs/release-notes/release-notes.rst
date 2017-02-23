==========================================================================
OPNFV Release Note for the Danube.1.0 release of OPNFV for SDN VPN feature
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
| **Repo/tag**                         | Danube.1.0                                |
|                                      |                                           |
+--------------------------------------+-------------------------------------------+
| **Release designation**              | Danube 1.0 follow-up release              |
|                                      |                                           |
+--------------------------------------+-------------------------------------------+
| **Release date**                     | March 23 2016                             |
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
ODL has been upgraded to Boron SR2.

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

Deliverables
------------

Software deliverables
~~~~~~~~~~~~~~~~~~~~~

- Fuel plugin for OpenStack BGPVPN
- Changes to ODL Fuel plugin to activate the NetVirt Karaf features
  and to apply the appropriate configuration. Also changes to
  implement integration with 6Wind Zrpcd and Quagga.
- Changes to Apex to enable a BGPVPN deployment.
- Integration of VPN Service functional tests and BGPVPN API tests into Functest framework
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

Yardstick uses the floating ip mechanism to connect to the instances using SSH.
Therefore, the default test cases have been replaced by the ones running tests on the
bare-metal servers. Feature specific Yardstick test cases have not been implemented,
we plan to add these in Danube 2.0.

Known issues
------------

Moving to the new NetVirt has caused a regression in which a subnet
cannot be both attached to a Router and Network associated to a VPN.
This has been worked around in the tests and the upstream bug is being
tracked.

Workarounds
-----------

Test results
============

The deployment scenarios have successfully deployed in OPNFV CI many
times and all Functest tests (general and feature specific) are
passing.

References
==========
