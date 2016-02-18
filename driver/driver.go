package driver

import (
	_ "bytes"
	"encoding/json"
	"fmt"
	"golang.org/x/net/websocket"
	"io/ioutil"
	"log"
	"net/http"
	"net/url"
	"reflect"
	"runtime"
	"strconv"
	"strings"
)

// Session-related constants
const (
	TEGA_ID = "anonymous"
	HOST    = "localhost"
	PORT    = 8888
)

// CRUD-related constants
const (
	GET    = "GET"
	PUT    = "PUT"
	DELETE = "DELETE"
	PATCH  = "PATCH"
)

// PUBSUB-related constants
const (
	SUBSCRIBE   = "SUBSCRIBE"
	UNSUBSCRIBE = "UNSUBSCRIBE"
	PUBLISH     = "PUBLISH"
	NOTIFY      = "NOTIFY"
	MESSAGE     = "MESSAGE"
	REQUEST     = "REQUEST"
	RESPONSE    = "RESPONSE"
)

// Tega protocol over WebSocket
const (
	SESSION = "SESSION"
	SESSIONACK = "SESSIONACK"
)

// Subscribe mode
const (
	LOCAL  = "local"
	GLOBAL = "global"
	SYNC   = "sync"
)

const (
	WEBSOCKET_PUBSUB_URL = "ws://%s:%s/_pubsub"
	ORIGIN_URL           = "http://%s/"
)

const (
	RPC = "RPC"
)

// Tega operation
type Operation struct {
	tegaId     string
	host       string
	port       int
	version    int
	ws         *websocket.Conn
	subscriber Subscriber
	rpcs       map[string]func(ArgsKwargs) (Result, error)
}

// args and kwargs for RPC
type ArgsKwargs struct {
	Args   []interface{}
	Kwargs map[string]interface{}
}

// Result returend by RPC
type Result struct {
	Res interface{} `json:"result"`
}

// NOTIFY message from tega server
type Notification struct {
	TegaId   string      `json:"tega_id"`
	Ope      string      `json:"ope"`
	Path     string      `json:"path"`
	Instance interface{} `json:"instance"`
}

// PUBLISH message to tega server
type Publish struct {
	Msg interface{} `json:"message"`
}

// PUBLISH message to tega server
type Message struct {
	Msg interface{} `json:"message"`
}

// Subscriber interface for call back functions on NOTIFY and MESSAGE
type Subscriber interface {

	// Driver initialization completed: SESSIONACK has just been received
	OnInit()

	// Data Change Notifications
	OnNotify(*[]Notification)

	// Published message
	OnMessage(channel string, tegaId string, message *Message)
}

// Returns a default Operation
func NewOperation(tegaId string, host string, port int, subscriber Subscriber, scope string) (*Operation, error) {

	var ope *Operation

	if tegaId == "" {
		tegaId = TEGA_ID
	}
	if host == "" {
		host = HOST
	}
	if port == 0 {
		port = PORT
	}

	url := fmt.Sprintf(WEBSOCKET_PUBSUB_URL, host, strconv.Itoa(port))
	origin := fmt.Sprintf(ORIGIN_URL, host)
	ws, err := websocket.Dial(url, "", origin)
	if err == nil {
		session := strings.Join([]string{SESSION, tegaId, scope}, " ")
		_, err = ws.Write([]byte(session))
		if err == nil {
			ope = &Operation{
				tegaId:     tegaId,
				host:       host,
				port:       port,
				version:    -1,
				ws:         ws,
				subscriber: subscriber,
				rpcs:       make(map[string]func(ArgsKwargs) (Result, error)),
			}
			err = ope.Subscribe(tegaId, LOCAL)
			if err != nil {
				log.Print(err)
			}
		}
	}

	go ope.wsReader()

	return ope, err
}

func (ope *Operation) wsReader() {
	var err error
	for {
		var wsMessage string
		err = nil
		err = websocket.Message.Receive(ope.ws, &wsMessage)
		if err == nil {
			lines := strings.Split(wsMessage, "\n")
			line := strings.Split(lines[0], " ")
			cmd := line[0]

			if cmd == SESSIONACK {
				remote_tega_id := line[1]
				log.Printf("SESSIONACK received from %s", remote_tega_id)
				ope.subscriber.OnInit()
				continue
			}

			params := line[1:]
			body := lines[1]

			switch cmd {
			case NOTIFY:
				notifications := &[]Notification{}
				log.Printf("NOTIFY received: %v", notifications)
				err = json.Unmarshal([]byte(body), notifications)
				if err == nil {
					ope.subscriber.OnNotify(notifications)
				}
			case MESSAGE:
				channel := params[0]
				tegaId := params[1]
				message := &Message{}
				log.Printf("MESSAGE received: %s %s %v", channel, tegaId, message)
				err = json.Unmarshal([]byte(body), message)
				if err == nil {
					ope.subscriber.OnMessage(channel, tegaId, message)
				}
			case REQUEST:
				seqNo := params[0]
				requestType := params[1]
				tegaId := params[2]
				path := params[3]
				log.Printf("REQUEST received: %s %s %s %s %v", seqNo, requestType, tegaId, path, body)
				switch requestType {
				case RPC:
					argsKwargs := ArgsKwargs{}
					json.Unmarshal([]byte(body), &argsKwargs)
					//--- Remote Procedure Call ---
					func_ := ope.rpcs[path]
					result, err := func_(argsKwargs)
					//-----------------------------

					body, err := json.Marshal(result)
					if err == nil {
						response := fmt.Sprintf("%s %s %s %s\n%s", RESPONSE, seqNo, RPC, tegaId, body)
						_, err = ope.ws.Write([]byte(response))
					} else {
						log.Print(err)
					}
				default:
					log.Printf("Unidentified request type: %s", requestType)
				}
			}
		}
		if err != nil {
			log.Fatal(err)
		}
	}
}

func (ope *Operation) urlEncode(path string, ephemeral bool) *string {
	values := url.Values{}
	if ope.version >= 0 {
		version := strconv.Itoa(ope.version)
		values.Add("version", version)
	}
	values.Add("tega_id", ope.tegaId)
	if ephemeral {
		values.Add("ephemeral", "True")
	}
	path = strings.Replace(path, ".", "/", -1)
	url := "http://" + ope.host + ":" + strconv.Itoa(ope.port) + "/" + path + "/?" + values.Encode()
	return &url
}

// CRUD read operation
func (ope *Operation) Get(path string, instance interface{}) error {
	url := ope.urlEncode(path, false)
	resp, err := http.Get(*url)
	defer resp.Body.Close()
	var body []byte
	if err == nil {
		body, err = ioutil.ReadAll(resp.Body)
		if err == nil {
			err = json.Unmarshal(body, instance)
		}
	}
	return err
}

func (ope *Operation) put(path string, instance interface{}, ephemeral bool) error {
	url := ope.urlEncode(path, ephemeral)
	var err error = nil
	var body []byte
	body, err = json.Marshal(instance)
	if err == nil {
		client := &http.Client{}
		var request *http.Request
		var response *http.Response
		request, err = http.NewRequest(PUT, *url, strings.NewReader(string(body)))
		response, err = client.Do(request)
		defer response.Body.Close()
	}
	return err
}

// CRUD create/update operation
func (ope *Operation) Put(path string, instance interface{}) error {
	return ope.put(path, instance, false)
}

// CRUD create/update operation for an ephemeral node
func (ope *Operation) PutE(path string, instance interface{}) error {
	return ope.put(path, instance, true)
}

// Sets the node ephemeral
func (ope *Operation) Ephemeral(path string) error {
	url := ope.urlEncode(path, false)
	var err error = nil
	if err == nil {
		client := &http.Client{}
		var request *http.Request
		var response *http.Response
		request, err = http.NewRequest(PATCH, *url, nil)
		response, err = client.Do(request)
		defer response.Body.Close()
	}
	return err
}

// CRUD delete operation
func (ope *Operation) Delete(path string) error {
	url := ope.urlEncode(path, false)
	var err error = nil
	if err == nil {
		client := &http.Client{}
		var request *http.Request
		var response *http.Response
		request, err = http.NewRequest(DELETE, *url, nil)
		response, err = client.Do(request)
		defer response.Body.Close()
	}
	return err
}

// Sends SUBSCRIBE to tega server
func (ope *Operation) Subscribe(path string, scope string) error {
	subscribe := strings.Join([]string{SUBSCRIBE, path, scope}, " ")
	_, err := ope.ws.Write([]byte(subscribe))
	return err
}

// Sends UNSUBSCRIBE to tega server
func (ope *Operation) Unsubscribe(path string) error {
	unsubscribe := strings.Join([]string{UNSUBSCRIBE, path}, " ")
	_, err := ope.ws.Write([]byte(unsubscribe))
	return err
}

// Sends PUBLISH to tega server
func (ope *Operation) Publish(path string, message *Message) error {
	body, err := json.Marshal(Message{Msg: *message})
	if err == nil {
		publish := fmt.Sprintf("%s %s\n%s", PUBLISH, path, body)
		_, err = ope.ws.Write([]byte(publish))
	}
	return err
}

// Registers RPC with tega server
func (ope *Operation) RegisterRpc(path string, rpc func(ArgsKwargs) (Result, error)) {
	ope.rpcs[path] = rpc
	funcFullName := runtime.FuncForPC(reflect.ValueOf(rpc).Pointer()).Name()
	funcNameSlice := strings.Split(funcFullName, ".")
	funcName := funcNameSlice[len(funcNameSlice)-1]
	funcStr := fmt.Sprintf("%%%s.%s", ope.tegaId, funcName)
	err := ope.PutE(path, funcStr)
	if err != nil {
		log.Print(err)
	}
}
