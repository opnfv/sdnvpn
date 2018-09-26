#! /bin/bash

set -xe
# change the password because this script is run on a passwordless cloud-image
echo 'ubuntu:opnfv' | chpasswd

# Wait for a floating IP
# as a workaround to NAT breakage
sleep 100

# Variables to be filled in with python
NEIGHBOR_IP={0}
OWN_IP={1}
# directly access the instance from the external net without NAT
EXT_NET_MASK={2}
IP_PREFIX={3}
RD={4}
IRT={5}
ERT={6}

if [[ $(getent hosts | awk '{{print $2}}') != *"$(cat /etc/hostname | awk '{{print $1}}')"* ]]
then
echo "127.0.1.1 $(cat /etc/hostname | awk '{{print $1}}')" | tee -a /etc/hosts
fi

quagga_int=''
for net_int in $(netstat -ia | awk 'NR>2{{print $1}}');
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

# Download quagga/zrpc rpms
cd /root
wget http://artifacts.opnfv.org/sdnvpn/quagga4/quagga-ubuntu-updated.tar.gz
tar -xvf quagga-ubuntu-updated.tar.gz
cd /root/quagga
dpkg -i c-capnproto_1.0.2.75f7901.Ubuntu16.04_amd64.deb
dpkg -i zmq_4.1.3.56b71af.Ubuntu16.04_amd64.deb
dpkg -i quagga_1.1.0.cd8ab40.Ubuntu16.04_amd64.deb
dpkg -i thrift_1.0.0.b2a4d4a.Ubuntu16.04_amd64.deb
dpkg -i zrpc_0.2.0efd19f.thriftv4.Ubuntu16.04_amd64.deb

nohup /opt/quagga/sbin/bgpd &

cat > /tmp/quagga-config << EOF1
config terminal
router bgp 200
 bgp router-id $OWN_IP
 no bgp log-neighbor-changes
 bgp graceful-restart stalepath-time 90
 bgp graceful-restart restart-time 900
 bgp graceful-restart
 bgp graceful-restart preserve-fw-state
 bgp bestpath as-path multipath-relax
 neighbor $NEIGHBOR_IP remote-as 100
 no neighbor $NEIGHBOR_IP activate
 vrf $RD
  rd $RD
  rt import $IRT
  rt export $ERT
 exit
!
address-family vpnv4
neighbor $NEIGHBOR_IP activate
neighbor $NEIGHBOR_IP attribute-unchanged next-hop
exit
!
route-map map permit 1
 set ip next-hop $OWN_IP
exit
!
router bgp 200
address-family vpnv4
network $IP_PREFIX rd $RD tag 100 route-map map
exit
!
EOF1

sleep 20

(sleep 1;echo "sdncbgpc";sleep 1;cat /tmp/quagga-config;sleep 1; echo "exit") |nc -q1 localhost 2605
