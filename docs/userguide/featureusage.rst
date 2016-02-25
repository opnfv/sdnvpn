.. This work is licensed under a Creative Commons Attribution 4.0 International License.
.. http://creativecommons.org/licenses/by/4.0
.. (c) Tim Irnich, (tim.irnich@ericsson.com)

SDN VPN capabilities and usage
================================
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
-----------------------------------------------

For the details of using OpenStack BGPVPN API, please refer to the documentation
at http://docs.openstack.org/developer/networking-bgpvpn/.
