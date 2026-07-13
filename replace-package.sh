#!/bin/bash
#
# Copyright (c) 2019-2020 P3TERX <https://p3terx.com>
#
# This is free software, licensed under the MIT License.
# See /LICENSE for more information.
#
# https://github.com/P3TERX/Actions-OpenWrt
# File name: replace-package.sh
# Description: OpenWrt DIY script  (After Update feeds)
#





#Replace golang feed
echo 'replace golang'
rm -rf feeds/packages/lang/golang
git clone https://github.com/sbwml/packages_lang_golang -b 26.x feeds/packages/lang/golang

echo 'replace v2ray-geodata'
rm -rf feeds/packages/net/v2ray-geodata
# git clone https://github.com/sbwml/luci-app-openlist2 package/openlist
git clone https://github.com/sbwml/luci-app-mosdns -b v5 package/mosdns
git clone https://github.com/sbwml/v2ray-geodata package/v2ray-geodata
