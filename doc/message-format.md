##tega messaging

In tega,
- REST APIs for CRUD 
- WebSocket for session management, pubsub and RPC.

"tega.messaging" package provides methods for synchronous request/response messaging over WebSocket.

##tega WebSocket message format
```
        seq_no                  = 1*DIGIT
        tega_id                 = 1*( ALPHA / DIGIT / "-" / "_" )
        TEGA-websocket-message  = Session / Subscribe / Unsubscribe / Publish /
                                  Notify / Message / Request / Response
        TEGA-scope              = "global" / "local" / "sync"
        Session                 = "SESSION" SP tega_id SP TEGA-scope
        Subscribe               = "SUBSCRIBE" SP path SP TEGA-scope
        Unsubscribe             = "UNSUBSCRIBE" SP path
        Notify                  = "NOTIFY" CRLF notifications
        Publish                 = "PUBLISH" SP channel CRLF message
        Message                 = "MESSAGE" SP channel SP tega_id CRLF message
        Request                 = "REQUEST" SP seq_no SP TEGA-request-type SP
                                   tega_id SP path CRLF body
        Response                = "RESPONSE" SP seq_no SP TEGA-request-type SP
                                   tega_id CRLF body
```
