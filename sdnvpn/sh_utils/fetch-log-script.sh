#!/bin/bash

### Configuration Required
set -e

tmp_folder=/tmp/opnfv-logs-$HOSTNAME/
rm -rf $tmp_folder
mkdir -p $tmp_folder

if [ "`whoami`" != "root" ]; then
  echo "You need to be root"
  exit 1
fi
#install needed packages
if ! which sshpass 2>&1 >> /dev/null;then
  yum install -y sshpass &> /dev/null || apt-get install -y sshpass &> /dev/null
fi
################# DPN Stauts #######################################################

############### Enable TRACE for org.opendaylight.vpnservice,Configuring KARAF file size to 50MB and clear OLD Logs

_enable_logs(){
  level=$1
  lib=$2
  echo "setting log level from $lib to $level"
  $KARAF "log:set $level $lib" 2>&1
}
logs_enable()
{
  set_to_trace=( org.opendaylight.vpnservice org.opendaylight.bgpmanager org.opendaylight.vpnservice.dhcpservice org.opendaylight.netvirt  org.opendaylight.netvirt.aclservice org.opendaylight.neutron org.opendaylight.netvirt.neutronvpn org.opendaylight.neutron )
  set_to_error=( org.opendaylight.openflowplugin )
  set_to_warn=( org.opendaylight.vpnservice.arputil org.opendaylight.vpnservice.alivenessmonitor org.opendaylight.vpnservice.interfacemgr.pmcounters org.opendaylight.genius.arputil org.opendaylight.genius.interfacemgr  org.opendaylight.genius.alivenessmonitor )
 echo
 echo
 echo "==================="
 echo "Enabled logs in ODL"
 echo "==================="
 echo

 for lib in $set_to_trace;do
   _enable_logs TRACE $lib
 done
 for lib in $set_to_error;do
   _enable_logs ERROR $lib
 done
 for lib in $set_to_warn;do
   _enable_logs WARN $lib
 done
 sleep 1
 echo "Removing existing karaf logs............"
 rm -rf /opt/opendaylight/data/log/karaf.log.*
 echo "Modifying karaf log file size to 50MB............"
 sed -i -e 's/log4j.appender.out.maxFileSize=1MB/log4j.appender.out.maxFileSize=50MB/g' /opt/opendaylight/etc/org.ops4j.pax.logging.cfg
 echo "Truncating karaf logs............"
 echo "truncated" >/opt/sdnc/opendaylight/data/log/karaf.log
}

logs_disable()
{
  set_to_info=( org.opendaylight.vpnservice org.opendaylight.bgpmanager org.opendaylight.vpnservice.dhcpservice org.opendaylight.netvirt  org.opendaylight.netvirt.aclservice org.opendaylight.neutron org.opendaylight.netvirt.neutronvpn org.opendaylight.neutron org.opendaylight.openflowplugin org.opendaylight.vpnservice.arputil org.opendaylight.vpnservice.alivenessmonitor org.opendaylight.vpnservice.interfacemgr.pmcounters org.opendaylight.genius.arputil org.opendaylight.genius.interfacemgr  org.opendaylight.genius.alivenessmonitor )
 echo
 echo
 echo "==========================="
 echo "set log to INFO logs in ODL"
 echo "==========================="
 echo

 for lib in $set_to_info;do
   _enable_logs INFO $lib
 done

}

log_command_exec(){
  file=$1
  touch $file
  shift
  cmd=$@
  echo "==========================================================" >> $file
  echo "$cmd" >> $file
  echo "==========================================================" >> $file
  $cmd 2>&1 >> $file
}

flows()
{
  flows=$tmp_folder/DPN-flows-groups-$HOSTNAME.txt
  log_command_exec "$flows" ovs-vsctl show
  log_command_exec "$flows" ovs-ofctl -O OpenFlow13 dump-flows br-int
  log_command_exec "$flows" ovs-ofctl -O OpenFlow13 dump-groups br-int
  log_command_exec "$flows" ovs-ofctl show br-int -O OpenFlow13
}

node(){
 node=$tmp_folder/$HOSTNAME.txt
 log_command_exec "$node" ifconfig -a
 files_folders=( /opt/opendaylight/data/log/ /var/log/openvswitch/ /var/log/neutron/)
 for ((i = 0; i < ${#files_folders[@]};i++));do
   if [ -e ${files_folders[$i]} ];then
     cp -r ${files_folders[$i]} $tmp_folder/
   fi
 done
 # not all messages only tail the last 10k lines
 tail -n 10000 /var/log/messages > messages
}

_curl_data_store(){
  file=$1
  url=$2
  touch $file
  echo "============================= $url ======================" >> $file
  curl --silent -u admin:admin -X GET http://$odl_ip_port/$url | python -mjson.tool 2>&1 >> $file
}

_get_output_karaf(){
  file=$1
  touch $file
  shift
  echo "============================ KARAF $@ ===================" >> $file
  sshpass -p karaf ssh -p 8101 -o "StrictHostKeyChecking no" karaf@localhost "$@" 2>&1 >> $file

}
datastore()
{

  dump=$tmp_folder/dump-$HOSTNAME.txt
  operational=$tmp_folder/Operational-Inventory-$HOSTNAME.txt
  karaf_output=$tmp_folder/Karaf_out-$HOSTNAME.txt
  odl_ip_port=$(grep ^url= /etc/neutron/plugins/ml2/ml2_conf.ini |cut -d '/' -f3)

  config_urls=( restconf/config/neutron:neutron/networks/ restconf/config/neutron:neutron/subnets/ restconf/config/neutron:neutron/ports/ restconf/config/neutron:neutron/routers/ restconf/config/itm:transport-zones/ restconf/config/itm-state:tunnels_state/ restconf/config/itm-state:external-tunnel-list/ restconf/config/itm-state:dpn-endpoints/ restconf/config/itm-config:vtep-config-schemas/ restconf/config/itm-config:tunnel-monitor-enabled/ restconf/config/itm-config:tunnel-monitor-interval/ restconf/config/interface-service-bindings:service-bindings/ restconf/config/l3vpn:vpn-instances/ restconf/config/ietf-interfaces:interfaces/ restconf/config/l3vpn:vpn-interfaces/ restconf/config/odl-fib:fibEntries restconf/config/neutronvpn:networkMaps restconf/config/neutronvpn:subnetmaps restconf/config/neutronvpn:vpnMaps restconf/config/neutronvpn:neutron-port-data restconf/config/id-manager:id-pools/ restconf/config/elan:elan-instances/ restconf/config/elan:elan-interfaces/ restconf/config/elan:elan-state/ restconf/config/elan:elan-forwarding-tables/ restconf/config/elan:elan-interface-forwarding-entries/ restconf/config/elan:elan-dpn-interfaces/ restconf/config/elan:elan-tag-name-map/  restconf/config/odl-nat:external-networks/ restconf/config/odl-nat:ext-routers/ restconf/config/odl-nat:intext-ip-port-map/ restconf/config/odl-nat:snatint-ip-port-map/ restconf/config/odl-l3vpn:vpn-instance-to-vpn-id/ restconf/config/neutronvpn:neutron-router-dpns/ restconf/operational/itm-config:tunnel-monitor-interval/ restconf/config/itm-config:tunnel-monitor-interval/ restconf/operational/itm-config:tunnel-monitor-params/ restconf/config/itm-config:tunnel-monitor-params/ restconf/config/vpnservice-dhcp:designated-switches-for-external-tunnels/ restconf/config/neutron:neutron/security-groups/ restconf/config/neutron:neutron/security-rules/ restconf/config/network-topology:network-topology/topology/hwvtep:1 restconf/config/network-topology:network-topology/topology/ovsdb:1 )

  for url in ${config_urls[@]};do
    _curl_data_store $dump $url
  done

  operational_urls=( restconf/operational/itm-state:tunnels_state/ restconf/operational/odl-interface-meta:bridge-ref-info/ restconf/operational/odl-l3vpn:prefix-to-interface/ restconf/operational/odl-l3vpn:vpn-instance-op-data/ restconf/operational/l3vpn:vpn-interfaces/ restconf/operational/ietf-interfaces:interfaces-state/ restconf/operational/odl-l3vpn:prefix-to-interface/ restconf/operational/l3nexthop:l3nexthop restconf/operational/elan:elan-instances/ restconf/operational/elan:elan-interfaces/ restconf/operational/elan:elan-state/ restconf/operational/elan:elan-forwarding-tables/ restconf/operational/elan:elan-interface-forwarding-entries/ restconf/operational/elan:elan-dpn-interfaces/ restconf/operational/elan:elan-tag-name-map/ restconf/operational/odl-nat:napt-switches/ restconf/operational/odl-nat:intext-ip-map/ restconf/operational/odl-nat:external-ips-counter/ restconf/operational/neutronvpn:neutron-router-dpns/ restconf/operational/odl-l3vpn:subnet-op-data/ restconf/operational/odl-l3vpn:port-op-data/ restconf/operational/odl-l3vpn:vpn-to-extraroute restconf/operational/neutronvpn:neutron-vpn-portip-port-data/ restconf/operational/odl-fib:label-route-map/ restconf/operational/itm-config:tunnel-monitor-interval/ restconf/operational/itm-config:tunnel-monitor-params/ restconf/operational/odl-interface-meta:if-indexes-interface-map/ restconf/operational/network-topology:network-topology/topology/hwvtep:1 restconf/operational/network-topology:network-topology/topology/ovsdb:1 restconf/operational/opendaylight-inventory:nodes/ restconf/operational/opendaylight-inventory:nodes/ )

  for url in ${operational_urls[@]};do
    _curl_data_store $operational $url
  done


  karaf_commands=( "display-bgp-config --debug" "bundle:list -s" fib-show "show-bgp --cmd 'ip bgp summary'" "show-bgp --cmd 'ip bgp neighbor'" "show-bgp --cmd 'ip bgp vpnv4 all summary'")
  for ((i = 0; i < ${#karaf_commands[@]}; i++));do
    _get_output_karaf $karaf_output ${karaf_commands[$i]}
  done
  # TODO check this one:
  # curl --silent -u admin:admin -H "Content-Type: application/json" --data "{"input" :  { } }" -X POST http://$OS_MIP:8181/restconf/operations/neutronvpn:getL3VPN | python -mjson.tool >>$file1
}

# check if running on karaf node
if netstat -atnp |grep 8101 -q;then
  datastore
fi
flows
node

pushd /tmp
rm -rf log_output.tar.gz
#tar -czvf dump_output-$HOSTNAME-`date +"%d-%m-%H-%M"`.tar.gz $tmp_folder
tar -czvf log_output.tar.gz $tmp_folder 2>&1

