#!/bin/bash
export bridges="admin|private|public|storage"
for br in $(ifconfig |grep -v br-external |grep "^br" |grep -E $bridges |awk '{print $1}');do
  sudo ip addr flush dev $br;
done
