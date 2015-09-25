[MVC](http://en.wikipedia.org/wiki/Model%E2%80%93view%E2%80%93controller)を参考に、今週(2014/9/2)色々と考えた事を絵に書いてみた。ネットワーク機器をデータベースに見立てると、このようになった。

![D-MVC](https://raw.githubusercontent.com/araobp/tega/master/doc/d-mvc.png)

データ実体はNOSが提供するCLIの先のデータベース,OVSDBやLinuxの/etc等にあるイメージで、ある程度抽象化されたtree構造のModel(当プロジェクトでは、これをtegaと呼ぶ)がネットワーク全体にまたがる。

チャレンジすべき事は、network-wide multi-version concurrency control (network-wide MVCC)
* mount (like NFS)
* tree-data snapshots　＝＞　コードを書いてみて、すこし実現出来た。
* network-wide lock (global/partial)
* atomicity and collision detection
* 'rwx' permission setting for each tree node　＝＞　たぶん、'x'はRPCなんだろうな？
* pub/sub ＝＞　notificaions

データベース技術を勉強し始めたが、NFSやrsyncも勉強すべきところがありそう。

やっぱり、オーケストレーション系は、OpenStackもそうだけど、メッセージキューや分散データベースの話になってくるみたい。

普通のLinuxサーバ向けだったら、ありものの何かを組み合わせればある程度は実現出来るかもしれないが、これらを、pythonベースの自作DBだけで実現出来るか？というのが、当プロジェクトが追求するところ。

また、CRUDに収まらない部分、即ち、RPCとnotificationsをどう実現するか？まだ、検討出来ていない。

一方、nlan(neutron-lan)でのMVCモデルは以下。DataのwriteはOne Wayのみサポート(agent側で設定変更した場合、masterとデータが自動的に同期出来ない)。Auto-rollbackも出来なかった(reset-rollbackは可)。
<pre>

       REST API
           |
    [rest.py(on WSGI)]           CLI
           ^                      ^
           |                      |
           +---------+  +---------+
                     |  |
                     V  V
       [schema]---[nlan.py]---[git repo]
                     ^  ^
                     |  |
                RPC(OrderedDict-based)
                     |  |
             +-------+  +--------+
             |                   |
[schema]     V                   V           [Schema]
[OVSDB]---[nlan_agent.py]   [nlan_agent.py]---[OVSDB]
             ^                   ^
             |                   |
            CLI                 CLI
             |                   |
             V                   V
          OpenWrt             OpenWrt
        OpenvSwitch         OpenvSwitch
</pre>
