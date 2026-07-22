# 🖥️ ImmortalWrt 24.10 (6.6 内核)

&gt; 基于 [padavanonly/immortalwrt-mt798x-24.10](https://github.com/Lihyrs/immortalwrt-mt798x-6.6)构建

---

## 📦 支持设备

| 设备 | 芯片 | 内存 | 状态 |
|------|------|------|------|
| 🟢 **CMCC RAX3000M** | MT7981 | 256MB |  |


---


## 🔌 预装插件

| 插件 | 说明 |
|------|------|
| 🌐 **openclash** | 代理插件，支持多种代理协议（如 Shadowsocks、VMess、Trojan 等），提供规则分流、策略组管理及 Web 控制面板 |
| 🛡️ **adguardhome** | DNS 去广告与隐私保护工具，支持自定义过滤规则、DNS 加密查询（DoH/DoT）及详细的查询日志统计 |
| 🌍 **zerotier** | 虚拟组网工具，创建安全的二层/三层虚拟局域网，实现跨地域设备互联，支持 Web 控制台管理 |
| 💾 **USB 支持** | 包括 USB 存储驱动（exFAT/NTFS/ext4 等文件系统支持）及 USB 网络适配器驱动（如 RNDIS、CDC-Ether 等） |
| 📂 **网络共享** | 基于 ksmbd 内核态 SMB 服务的文件共享，搭配 openlist2 实现局域网内文件访问与权限管理 |
| ⚡ **MTK 硬件加速** | 开启 MediaTek 专用网络加速引擎（如 PPE/HNAT），降低 CPU 负载，提升路由转发性能及吞吐量 |

---

## 🌐 网络信息

| 项目 | 默认值 |
|------|--------|
| 🔗 登录地址 | `192.168.1.1` |
| 🔑 登录密码 | 无 |
| 📶 WiFi 名称 | `immortalwrt-2.4G` / `immortalwrt-5G` |
| 📶 WiFi 密码 | 无 |
| 🐧 内核版本 | 6.6 |

---

## 项目特点：

- 通过仓库根目录下的 `feeds-config.yml` 文件来管理第三方 feeds（软件源）。该文件支持同时定义多个 feed，并允许为每个 feed 单独指定要拉取的软件包列表以及是否强制覆盖安装。


## Feeds 配置文件 (`feeds-config.yml`)

### 文件格式

```yaml
feeds:
  - name: <feed名称>                # 必填，用作 feed 标识
    repo: <git仓库地址>             # 必填，feed 仓库的克隆 URL
    repo_branch: <分支或标签>        # 可选，要克隆的分支或标签（默认使用仓库默认分支）
    packages:                      # 可选，要从该 feed 中复制的软件包目录列表
      - package1
      - package2
      # ...
    overwrite: <true|false>        # 可选，是否对该 feed 强制安装（默认 false）
```
#### 字段说明

|字段| 类型  |  描述|
|:---|:---:|:---|
|name  |  string  |  必填。 该 feed 的唯一名称。将用作` feeds.conf.default` 中的 feed 名称（例如 `src-git <name> ...` 或 `src-link mypkg_<name>`）。|
|repo  |  string  |  必填。 feed 仓库的 Git URL。|
|repo_branch  |  string  |  可选。 要克隆的分支或标签。如果省略，则使用仓库的默认分支。|
|packages  |  list  |  可选。 要从克隆的 feed 中复制到本地软件包树的软件包目录列表。如果此列表为空或省略，则该 feed 会作为标准的 `src-git` 条目添加。如果指定了软件包，则会克隆整个仓库，但仅将列出的子目录复制到` pkg/<name>/`，并在 `feeds.conf.default` 中添加 `src-link mypkg_<name>` 条目。
|overwrite  |  boolean  |  可选。 如果设置为 true，则在 `./scripts/feeds install` 期间对该 feed 使用 `-f` 标志强制安装（仅影响该 feed）。默认为 `false`。|

#### 工作原理
1. **未列出 packages**

    会在 `feeds.conf.default` 中添加一行 `src-git`：

```text
    src-git <name> <repo>[;<branch>]
```
2. **列出了 packages**

会克隆仓库，仅将指定的软件包目录复制到 `pkg/<name>`/，然后添加 src-link：

```text
    src-link mypkg_<name> $GITHUB_WORKSPACE/pkg/<name>
```
    这样您就可以从大型 feed 中按需选取所需的软件包。

3. `overwrite: true`

    在 feed 安装阶段，正常执行 `install -a` 之后，会额外运行：

```text
    ./scripts/feeds install -a -f -p <name>
```
    以强制覆盖该 feed 中的任何已有软件包。

#### 示例
```yaml
feeds:
  - name: sm
    repo: https://github.com/*/*.git
    packages:
      - luci-app-adguardhome
      - adguardhome
      - luci-app-openclash

  - name: q*
    repo: https://github.com/*/*.git
    repo_branch: main
    overwrite: true
```
在这个示例中：

`small-package` 会作为 `src-link` 添加，只会复制列表中的三个软件包。

`qmodem` 因为未指定 `packages`，会作为 `src-git` 添加，并且会强制安装`（overwrite: true）`。

注意事项
工作流会自动安装 `yq` 工具（如果未安装）以解析 YAML 文件。


## Credits

- [Microsoft Azure](https://azure.microsoft.com)
- [GitHub Actions](https://github.com/features/actions)
- [OpenWrt](https://github.com/openwrt/openwrt)
- [Lean's OpenWrt](https://github.com/coolsnowwolf/lede)
- [tmate](https://github.com/tmate-io/tmate)
- [mxschmitt/action-tmate](https://github.com/mxschmitt/action-tmate)
- [csexton/debugger-action](https://github.com/csexton/debugger-action)
- [Cowtransfer](https://cowtransfer.com)
- [WeTransfer](https://wetransfer.com/)
- [Mikubill/transfer](https://github.com/Mikubill/transfer)
- [softprops/action-gh-release](https://github.com/softprops/action-gh-release)
- [ActionsRML/delete-workflow-runs](https://github.com/ActionsRML/delete-workflow-runs)
- [dev-drprasad/delete-older-releases](https://github.com/dev-drprasad/delete-older-releases)
- [peter-evans/repository-dispatch](https://github.com/peter-evans/repository-dispatch)

## License

[MIT](https://github.com/P3TERX/Actions-OpenWrt/blob/main/LICENSE) © [**P3TERX**](https://p3terx.com)
