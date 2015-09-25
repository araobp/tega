OIDの自動生成
============

SNMPのMIBにしろ、YANGのmoduleにしろ、OID(Object ID)の生成とOIDが指し示すデータへのアクセスが面倒。ここを容易化するとプログラミングが楽になる。従い、tega では\__dict\__[key]をOIDとして使い(即ちobjectのattribute)、かつ、attributeの自動生成をサポートする。

＿call＿(self, **kwargs)でOID自動生成
-----------------------------------
\__call\__(**key)にてfrozendict(key)を＿dict＿のkeyとする事で [YANGのlistやkey相当](http://tools.ietf.org/html/rfc6020#section-7.8)を実現する事にした。[frozendict](https://pypi.python.org/pypi/frozendict/0.4)は、dict的なclassで、かつ、hashを生成出来るため、＿dict＿のkeyとして使える。
<pre>
a.b(id=1, name='alice').c ＝＞ a.＿getattr＿('b').＿call＿(id=1, name='alice').＿getattr＿('c')
a.b(id=2, name='bob').c ＝＞ a.＿getattr＿('b').＿call＿(id=2, name='bob').＿getattr＿('c')
           :
</pre>

\__call\__(...)でOID生成した場合、以下のような記述は不可：
<pre>
a.b(id=1) = 'alice' は不可

a.b(id=1).name = 'alice' は可
</pre>

＿getattr＿(self, key)や＿setattr＿(self, key, value)でOID自動生成
----------------------------------------------------------------
<pre>
a.b[0].c ＝＞ a.＿getattr＿('b').＿getattr＿(0).＿getattr＿('c')
a.b[1].c ＝＞ a.＿getattr＿('b').＿getattr＿(1).＿getattr＿('c')
    :

（注) __getattr__や__setattr__は keyとして int 型も受け付けるみたい。
</pre>

＿call＿(self)で値なしのOID生成
----------------------------
[YANGにおけるpresence](http://tools.ietf.org/html/rfc6020#section-7.5.1)相当は、引数なしで＿call＿(self)する事で生成する事にした。OID自体に意味を持たせる場合に使う。
<pre>
a.b(id=1, name='alice')() ＝＞ a.__getattr__('b').＿call＿(id=1, name='alice').＿call＿()
a.b(id=2, name='bob')() ＝＞ a.__getattr__('b').＿call＿(id=2, name='bob').＿call＿()
           :
</pre>

配列の自動生成
------------
a.b.c[0]はa.b.c.0と同じだが、Python interpreter上では後者の記述は出来ない。

a.b.c.append_(...)みたいなものは検討中。この場合、最初に[]でつくったattributeが数字(int, long)だったら、Pythonのlist相当と判断。
<pre>
(1)
a.b.c[100].name = 'alice'
a.b.c.append_().name = 'bob'＝＞a.b.c[101].name = 'bob'
(2)
a.b.c[100] = 'alice'
a.b.c.append_('bob') ＝＞　a.b.c[101] = 'bob'
</pre>

特にversion管理しなくて良いデータの場合、以下の記述を推奨（動作が軽い）：
<pre>
a.b.c = []
a.b.c.append('alice')
a.b.c.append('bob')
name1, name2 = a.b.c
print name1, name2
'alice' 'bob'
</pre>

OID使用における注意事項
--------------------
<pre>
a.b.c(id=1, name='alice').gender = 'female'
a.b.c(id=1, name='alice').phone = '111-2222'
             :
でなく、
oid = a.b.c(id=1, name='alice')
oid.gender = 'female'
oid.phone = '111-2222'
      :
を推奨。この方が動作が軽い。
</pre>


tega以外のobject結合時
-------------------
<pre>
a.b.c = object
a.b.c(...)はobjectの__call__(...)を呼び出す。
a.b.c.d(...)はobjectのd(...)を呼び出す。
</pre>
tegaでは、tega以外のobjectでもversion管理が可能となっている。

＿setattr＿におけるSchemaとの連携（実装予定）
--------------------------------------

* def ＿setattr＿(self,key,value): にて key に相当する schemaを取得し、valueが妥当かチェックする。
* keyに相当するschemaがない場合や、schemaで定義されるtypeやpatternに沿わないvalueの場合、exceptionをraiseする。
* tree7047では、schemaからmetaclassやdescriptors(Javaのgetter/setterメソッド相当)を自動生成しない。schemaはPythonのdictデータへ変換し、＿setattr＿にて参照する。このdictデータは、NB APIs/CLIs自動生成においても参照される。


