.. This work is licensed under a Creative Commons Attribution 4.0 International License.
.. http://creativecommons.org/licenses/by/4.0
.. (c) Tim Irnich, (tim.irnich@ericsson.com) and others

SDN VPN feature overview
========================
.. Describe the specific features and how it is realised in the scenario in a brief manner
.. to ensure the user understand the context for the user guide instructions to follow.

Many telecom network functions are relying on layer-3 infrastructure services, within a VNF
between components, or towards existing external networks. In many cases, these external
networks are implemented in MPLS/BGP technology in existing service provider wide-area-networks (WAN).
This proven technology provides a good mechanism for inter-operation of a NFV Infrastructure (NFVI)
and wide-area networks (WAN) and is the main feature set provided by the BGP VPN project.

SDN VPN capabilities and usage
==============================
.. Describe the specific capabilities and usage for <XYZ> feature.
.. Provide enough information that a user will be able to operate the feature on a deployed scenario.

The BGPVPN feature enables creation of BGP VPNs according to the OpenStack
BGPVPN blueprint at https://blueprints.launchpad.net/neutron/+spec/neutron-bgp-vpn.
In a nutshell, the blueprint defines a BGPVPN object and a number of ways
how to associate it with the existing Neutron object model, including a unique
definition of the related semantics. The BGPVPN framework supports a backend
driver model with currently available drivers for Bagpipe, OpenContrail, Nuage
and OpenDaylight.

Currently, in OPNFV only ODL is supported as a backend for BGPVPN. API calls are
mapped onto the ODL VPN Service REST API through the BGPVPN ODL driver and the
ODL Neutron Northbound module.

Feature and API usage guidelines and example
--------------------------------------------
.. Describe with examples how to use specific features, provide API examples and details required to
.. operate the feature on the platform.

For the details of using OpenStack BGPVPN API, please refer to the documentation
at http://docs.openstack.org/developer/networking-bgpvpn/.

