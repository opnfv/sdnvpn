.. This work is licensed under a Creative Commons Attribution 4.0 International License.
.. http://creativecommons.org/licenses/by/4.0
.. (c) Tim Irnich  (tim.irnich@ericsson.com)

.. _Configuring-SDNVPN-features
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

