## REST と WebSocket の併用

tega dbはRESTとWebSocketベースのAPIを提供する：
- REST APIはCRUDオペレーションやtega dbマネージメントに適用
- WebSocketはpubsub(messaging)やRPC関連に適用（tega db内部動作向け）

tega CLIはREST APIを使ってtega dbを操作する。-s(--subscriber)オプション付きでCLIを起動すると、pubsub機能も操作できるが、これはデバッグ用機能。

## Session management

tega driverはtega serverとの通信に REST APIとWebSocketを併用する。WebSocketを使う理由は、NATやHTTP Proxyトラバーサルをサポートするため。

session_idはUUID。WebSockeｔを通して"SESSION session_id"を送信。PUTのurl paramにsession_idを付与する事で、WebSocketとREST APIを紐付ける。

```
Master                                Slave
   |                                   |
   |<--- SESSION session_id -----------|  WebSocket
   |                                   |
   |<--- PUT with session_id param ----|  REST
   |---- 200 OK ---------------------->|
   |                                   |
```

## tega ID
- tega IDはtega dbを更新するアプリの識別子。
- cliやdriver等は、session_idとしてtega IDを指定する事が可能。この場合、ネットワーク全体で一意なIDを指定する必要がある。
- session_idにUUIDではなくtega IDを使う事を推奨。tega IDを使う事で、ログ上で、どのアプリがどのような更新を行ったかが一目で判明し、トラブルシュートが容易化される。

