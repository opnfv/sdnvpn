.. This work is licensed under a Creative Commons Attribution 4.0 International License.
.. http://creativecommons.org/licenses/by/4.0
.. (c) Tim Irnich  (tim.irnich@ericsson.com)

Configuring SDNVPN features
---------------------------

Fuel installer configuration
<Niko: explain which settings have to / can be chosen in Fuel to get SDN VPN
deployed.>

Feature configuration
No post-deploy configuration is necessary. The Fuel BGPVPN plugin and the ODL
plugin should set up the cluster in a way that it is ready for BGPVPNs being
created. This includes the set-up of internal VxLAN transport tunnels between
compute nodes.

No post-configuration activities are required.

