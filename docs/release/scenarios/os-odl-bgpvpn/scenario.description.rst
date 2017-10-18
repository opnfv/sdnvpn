.. This work is licensed under a Creative Commons Attribution 4.0 International License.
.. http://creativecommons.org/licenses/by/4.0
.. (c) Tim Irnich (tim.irnich@ericsson.com) and Nikolas Hermanns (nikolas.hermanns@ericsson.com)

Introduction
============
.. In this section explain the purpose of the scenario and the types of capabilities provided

Many Telecom network functions are relying on layer-3 infrastructure
services, within a VNF between components, or towards existing external
networks. In many cases, these external networks are implemented in
MPLS/BGP technology in existing service provider wide-area-networks
(WAN). This proven technology provides a good mechanism for
inter-operation of a NFV Infrastructure (NFVI) and wide-area networks
(WAN) and is the main capability provided by the OPNFV SDNVPN project.

.. should we explain here what a deployment scenario is?

The OPNFV SDNVPN feature is made available through additional OPNFV
deployment scenarios, which is derived from the baseline
os-odl-nofeature scenario.

The BGPVPN feature enables creation of BGP VPNs on the Neutron API
according to the OpenStack BGPVPN blueprint at
https://blueprints.launchpad.net/neutron/+spec/neutron-bgp-vpn. In a
nutshell, the blueprint defines a BGPVPN object and a number of ways how
to associate it with the existing Neutron object model, as well as a
unique definition of the related semantics. The BGPVPN framework
supports a backend driver model with currently available drivers for
Bagpipe, OpenContrail, Nuage and OpenDaylight. The OPNFV scenario makes
use of the OpenDaylight driver and backend implementation through the
ODL NetVirt project.



Scenario components and composition
===================================
.. In this section describe the unique components that make up the scenario,
.. what each component provides and why it has been included in order
.. to communicate to the user the capabilities available in this scenario.

The SDN VPN feature enhances OPNFV's baseline OpenStack deployment with
the possibility to configure BGP based VPNs using the Neutron API
extension and service plugin provided by the OpenStack Neutron Stadium
project BGPVPN. The BGPVPN project consists of a Neutron API extension
and a service plugin which has a driver framework similar to the ML2
plugin. BGPVPN today has a quite large number of backend drivers
(Bagpipe, OpenContrail, Nuage and OpenDaylight currently). In OPNFV,
currently only the OpenDaylight driver is supported.

The BGPVPN ODL driver maps the BGPVPN API onto the OpenDaylight NetVirt
service, which exposes the data center overlay like a virtual router to
which Neutron Networks and Routers (and in the future also Ports) are
connected. NetVirt has access to the state of the Neutron API through
the OpenDaylight Neutron Northbound Interface module, which has been
enhanced to support the BGPVPN API extension. It uses an internal mesh
of VxLAN tunnels to interconnect the vSwitches on the data center
compute nodes. For the purpose of BGP based route exchange with other
BGP speakers the ODL controller makes use of Quagga BGP as an external
BGP speaker.


Scenario usage overview
=======================
.. Provide a brief overview on how to use the scenario and the features available to the
.. user.  This should be an "introduction" to the user guide document, and explicitly link to it,
.. where the specifics of the features are covered including examples and API's

  When would I use this scenario, what value does it provide?  Refer to the user guide for details
  of configuration etc...

Configuring SDNVPN features
---------------------------

Each installer has specific procedures to deploy the OPNFV platform so that the SDNVPN feature is enabled.

Fuel installer configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To install the SDNVPN feature using Fuel, follow the Fuel installation guide ensuring to select the SDNVPN
feature when prompted <add link to Fuel docs once artifact locations are known>.

This will trigger installation of the OpenStack BGPVPN API extension for
Neutron, set up for using the ODL driver, in addition to vanilla Neutron.
In addition, the required karaf features will be activated when ODL is installed and the compute nodes
will be configured including the VPN Service internal transport tunnel mesh.

No post-deploy configuration is necessary. The Fuel BGPVPN plugin and the ODL plugin
should set up the cluster ready for BGPVPNs being created.

APEX installer configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To install the SDNVPN feature using the APEX installer, follow the APEX installation guide and
activate the SDNVPN feature when prompted.

Limitations, Issues and Workarounds
===================================
.. Explain scenario limitations here, this should be at a design level rather than discussing
.. faults or bugs.  If the system design only provide some expected functionality then provide
.. some insight at this point.

Currently, in OPNFV only ODL is supported as a backend for BGPVPN. API calls are
mapped onto the ODL NetVirt REST API through the BGPVPN ODL driver and the
ODL Neutron Northbound module.

No DPDK-enabled vhost user ports are supported.

Integration with data center gateway will not work due to missing OVS patches for MPLSoGRE.

References
==========

For more information on the OPNFV Danube release, please visit
http://www.opnfv.org/danube
