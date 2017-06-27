#! /bin/bash

set -xe

# change the password because this script is run on a passwordless cloud-image
echo 'ubuntu:opnfv' | chpasswd

# Wait for a floating IP
# as a workaround to NAT breakage
sleep 20

# Variables to be filled in with python
NEIGHBOR_IP=%s
OWN_IP=%s
# directly access the instance from the external net without NAT
EXT_NET_MASK=%s

if [[ $(getent hosts | awk '{print $2}') != *"$(cat /etc/hostname | awk '{print $1}')"* ]]
then 
echo "127.0.1.1 $(cat /etc/hostname | awk '{print $1}')" | tee -a /etc/hosts
fi

quagga_int=''
for net_int in $(netstat -ia | awk 'NR>2{print $1}');
do
if [ -z "$(ifconfig | grep $net_int)" ]
then
quagga_int=$net_int
break
fi
done
if [ -z "$quagga_int" ]
then
echo 'No available network interface'
fi

ip link set $quagga_int up
ip addr add $OWN_IP/$EXT_NET_MASK dev $quagga_int

ZEBRA_CONFIG_LOCATION="/etc/quagga/zebra.conf"
DAEMONS_FILE_LOCATION="/etc/quagga/daemons"
BGPD_CONFIG_LOCATION="/etc/quagga/bgpd.conf"
BGPD_LOG_FILE="/var/log/bgpd.log"

# Quagga is already installed to run as well in setups without inet
# dns fix
# echo "nameserver 8.8.8.8" > /etc/resolvconf/resolv.conf.d/head
# resolvconf -u
# DEBIAN_FRONTEND=noninteractive apt-get update
# DEBIAN_FRONTEND=noninteractive apt-get install quagga -y

touch $BGPD_LOG_FILE
chown quagga:quagga $BGPD_LOG_FILE

chown quagga:quagga $DAEMONS_FILE_LOCATION
cat <<CATEOF > $DAEMONS_FILE_LOCATION
zebra=yes
bgpd=yes
ospfd=no
ospf6d=no
ripd=no
ripngd=no
isisd=no
babeld=no
CATEOF

touch $ZEBRA_CONFIG_LOCATION
chown quagga:quagga $ZEBRA_CONFIG_LOCATION

cat <<CATEOF > $BGPD_CONFIG_LOCATION
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
CATEOF
chown quagga:quagga $BGPD_CONFIG_LOCATION
service quagga restart
pgrep bgpd
pgrep zebra
# Start checking for accepted BGP routes
while true; do
accepted_routes_list=$(sudo vtysh -c 'show ip bgp neighbor' | grep 'accepted prefixes' | awk '{print $1}')
status="KO"
for i in $accepted_routes_list; do
if [ $i -gt "0" ]; then
status="OK"
break
fi
done
# Print "Routes: KO" if no routes where accepted else print "Routes: OK"
echo "Routes: $status, Cloud-init finished"
sleep 1
done
