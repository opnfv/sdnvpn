.. This work is licensed under a Creative Commons Attribution 4.0 International License.
.. http://creativecommons.org/licenses/by/4.0
.. (c) <optionally add copywriters name>

Introduction
============
.. In this section explain the purpose of the scenario and the types of capabilities provided

Many telecom network functions are relying on layer-3 infrastructure services, within a VNF
between components, or towards existing external networks. In many cases, these external
networks are implemented in MPLS/BGP technology in existing service provider wide-area-networks (WAN).

This proven technology provides a good mechanism for inter-operation of a NFV Infrastructure (NFVI)
and wide-area networks (WAN) and is the main capability provided by the OPNFV SDNVPN project.

.. should we explain here what a deployment scenario is?
The OPNFV SDNVPN feature is made available through additional OPNFV deployment scenarios, which are derived 
from the baseline scenarios os-odl_l2-nofeature and os-pdl_l3-nofeature. This document 
provides an outline of the os-odl_l2-bgpvpn scenarios of OPNFV including guidelines and references to 
required installation, software and hardware configuration documents.

Scenario components and composition
===================================
.. In this section describe the unique components that make up the scenario,
.. what each component provides and why it has been included in order
.. to communicate to the user the capabilities available in this scenario.

The SDN VPN feature enhances OPNFV's baseline OpenStack deployment with the
possibility to configure BGP based VPNs according to the OpenStack Neutron
Stadium project BGPVPN. The BGPVPN project consists of a Neutron API extension and a 
service plugin which has a driver framework simnilar to the ML2 plugin. BGPVPN today 
has a quyite large number of backend drivers (Bagpipe, OpenContrail,
Nuage and OpenDaylight currently). In OPNFV, currently only the OpenDaylight driver
is supported.

The BGPVPN ODL driver maps the BGPVPN API onto the OpenDaylight VPNService, which exposes the data 
center overlay like a virtual router to which Neutron Networks and Routers (and in the future also Ports) 
are connected. The VPNService has access to the state of the Neutron API through the OpenDaylight 
Neutron Northbound Interface module, which has been enhanced to support the BGPVPN API extension. 
It uses an internal mesh of GRE tunnels to interconnect the vSwitches on the data 
center compute nodes. For the purpose of BGP based route exchange with other BGP speakers the ODL 
controller makes use of Quagga BGP as an external BGP speaker. 

  <To be completed, this outlines the basic content and flow>
  Description of bgpvpn scenarios
  Description of the internal transport tunnel mesh
  Install Neutron BGPVPN additions (networking-bgpvpn)
  Neutron odl additions (networking-odl)
  install and configure Quagga (incl. config on ODL side)
  configure OVS to connect to ODL and set up the right bridges (network architecture)
  set up iptables to allow connections between OVS and ODL
  set up HA proxy so that ODL can be reached

  <Where applicable and without copying the installation procedure in the install guides>
  Describe Neutron BGPVPN additions (networking-bgpvpn)
  Neutron odl additions (networking-odl)
  Usage and the role of Quagga (incl. config on ODL side)
  OVS and ODL specifics around setting up the right bridges (network architecture)
  "" iptables to allow connections between OVS and ODL
  "" HA proxy so that ODL can be reached

Scenario usage overview
=======================
.. Provide a brief overview on how to use the scenario and the features available to the
.. user.  This should be an "introduction" to the userguide document, and explicitly link to it,
.. where the specifics of the features are covered including examples and API's

  When would I use this scenario, what value does it provide?  Refer to the userguide for details
  of configuration etc...

  Configuring SDNVPN features
---------------------------

Fuel installer configuration

In order to install the BGPVPN feature, the corresponding checkbox in Fuel has to be
selected. This will trigger installation of the OpenStack BGPVPN API extension for
Neutron (set up for using the ODL driver).

In addition, ODL has to be installed, see the corresponding section in the respective
installer documentation on how to install ODL. If the BGPVPN feature is installed,
ODL will automatically be installed with VPN Service karaf feature activated.

No post-deploy configuration is necessary. The Fuel BGPVPN plugin and the ODL plugin
should set up the cluster ready for BGPVPNs being created. This includes the set-up
of internal VxLAN transport tunnels between compute nodes.

No post-configuration activities are required.
  
Limitations, Issues and Workarounds
===================================
.. Explain scenario limitations here, this should be at a design level rather than discussing
.. faults or bugs.  If the system design only provide some expected functionality then provide
.. some insight at this point.

Currently, in OPNFV only ODL is supported as a backend for BGPVPN. API calls are
mapped onto the ODL VPN Service REST API through the BGPVPN ODL driver and the
ODL Neutron Northbound module.

Are there places these basic procedures will not work.  Do we have constraints on the use of
Quagga that may change in the future?

References
==========

For more information on the OPNFV Colorado release, please visit
http://www.opnfv.org/colorado
