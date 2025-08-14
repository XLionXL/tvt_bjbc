#!/bin/bash
# Author: jia.w@timevary.com
# Description: upgrade fusion algorithm
# parameter1: absolute path for upgrade dir
# parameter2: absolute path upgrade file tar.gz
#--------------------------------------------------------------------
if [ $# -ne 2 ];
then
echo "call this upgrade need two parameter with the upgrade_dir and upgrade_file.tar.gz"
echo "usage: "
echo "upgrade.sh upgrade_dir upgrade_file.tar.gz"
exit
fi
# shellcheck disable=SC2046
workdir=$(cd $(dirname "$0") || exit; pwd)
echo "workdir is ${workdir}"

upgrade_dir=$1
if [ ! -d "${upgrade_dir}" ];then
  echo "not exist upgrade dir ${upgrade_dir}"
  exit
fi
instance_prefix=$(basename "${upgrade_dir}")
echo "instance_prefix is ${instance_prefix}"
upgrade_file=$2
if [ ! -e "${upgrade_file}" ];then
  echo "not exist upgrade file ${upgrade_file}"
  exit
fi
upgrade_file_dir=${workdir}/upgrade
if [ ! -d "${upgrade_file_dir}" ];then
  mkdir -p "${upgrade_file_dir}"
fi
if [ "${upgrade_file_dir}" != "$(dirname "${upgrade_file}")" ];then
  # shellcheck disable=SC2086
  mv "${upgrade_file}" ${upgrade_file_dir}
  upgrade_file=${upgrade_file_dir}/$(basename "${upgrade_file}")
fi

# stop zipx.s.service
echo "stop zipx.s.service"
sudo systemctl stop zipx.s.service
sleep 3

cd "${upgrade_dir}" || exit
rm /usr/bin/zipx/zj-guard/*.py

sudo chmod a+rw ./*
# copy upgrade file to upgrade dir
echo "release upgrade file ${upgrade_file} to ${upgrade_dir}"
cd "${workdir}" || exit
# shellcheck disable=SC2086
extName=${upgrade_file##*.}
if [ "${extName}" == "gz" ]; then
  tar -xzf ${upgrade_file} -C ${upgrade_dir}
elif [ "${extName}" == "zip" ]; then
#  sudo unzip -P tvt_0123456789_2018 -oqd ${upgrade_dir} ${upgrade_file}
  sudo 7z x -ptvt_0123456789_2018 ${upgrade_file} -y -aoa -o${upgrade_dir}
elif [ "${extName}" == "7z" ]; then
  sudo 7z x -ptvt_0123456789_2018 ${upgrade_file} -y -aoa -o${upgrade_dir}
fi
chmod -R 777 ${upgrade_dir}

echo "upgrade ntp_face zj-guard-so"
cd "${workdir}"
rm -rf "${workdir}"/tvtupdate
if [ -e /usr/bin/zipx/zj-guard/tvtupdate.zip ];then
	unzip -o /usr/bin/zipx/zj-guard/tvtupdate.zip -d /usr/bin/zipx/zj-guard/
fi

if [ -e /usr/bin/zipx/zj-guard/tvtupdate/s.sh ];then
	chmod 777 /usr/bin/zipx/zj-guard/tvtupdate/s.sh
	
sudo /usr/bin/zipx/zj-guard/tvtupdate/s.sh
fi
echo "upgrade ntp_face zj-guard-so finish"

echo "rm /usr/bin/zipx/upgrade"
rm -rf /usr/bin/zipx/upgrade/*.zip

# start zipx.s.service
echo "start zipx.s.service"
sudo chmod 777 ${upgrade_dir}/python3_main_py
sudo systemctl restart zipx.s.service
sleep 3
# query service  status
sudo systemctl status zipx.s.service



