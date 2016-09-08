#! /bin/bash

set -xe

# Variables to be filled in with python
NEIGHBOR_IP=%s
OWN_IP=%s

ZEBRA_CONFIG_LOCATION="/etc/quagga/zebra.conf"
DAEMONS_FILE_LOCATION="/etc/quagga/daemons"
BGPD_CONFIG_LOCATION="/etc/quagga/daemons"
BGPD_LOG_FILE="/var/log/bgpd.log"

DEBIAN_FRONTEND=noninteractive apt-get install quagga -y

touch $BGPD_LOG_FILE
chown quagga:quagga $BGPD_LOG_FILE

chown quagga:quagga $DAEMONS_FILE_LOCATION
cat <<EOF > $DAEMONS_FILE_LOCATION
zebra=yes
bgpd=yes
ospfd=no
ospf6d=no
ripd=no
ripngd=no
isisd=no
babeld=no
EOF

touch $ZEBRA_CONFIG_LOCATION
chown quagga:quagga $ZEBRA_CONFIG_LOCATION

cat <<EOF > $BGPD_CONFIG_LOCATION
! -*- bgp -*-

hostname bgpd
password sdncbgpc

router bgp 200
 bgp router-id ${OWN_IP}
 neighbor ${NEIGHBOR_IP} remote-as 100
 no neighbor ${NEIGHBOR_IP} activate
!
 address-family vpnv4 unicast
 neighbor ${NEIGHBOR_IP} activate
 exit-address-family
!
line vty
 exec-timeout 0 0
!
debug bgp events
debug bgp  updates
log file ${BGPD_LOG_FILE}
end
EOF
chown quagga:quagga $BGPD_CONFIG_LOCATION

pgrep bgpd
pgrep zebra
