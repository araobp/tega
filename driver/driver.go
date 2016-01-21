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
)

// PUBSUB-related constants
const (
	SUBSCRIBE   = "SUBSCRIBE"
	UNSUBSCRIBE = "UNSUBSCRIBE"
)

// Tega protocol over WebSocket
const (
	SESSION = "SESSION"
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

// Tega operation
type Operation struct {
	tegaId     string
	host       string
	port       int
	version    int
	path       string
	ws         *websocket.Conn
	subscriber Subscriber
}

// NOTIFY message from tega server
type Notify struct {
	TegaId   string      `json:"tega_id"`
	Ope      string      `json:"ope"`
	Path     string      `json:"path"`
	Instance interface{} `json:"instance"`
}

// Subscriber interface for call back functions on NOTIFY
type Subscriber interface {
	OnNotify(*[]Notify)
}

// Returns a default Operation
func NewOperation(tegaId string, host string, port int, subscriber Subscriber) (*Operation, error) {

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
		session := strings.Join([]string{SESSION, tegaId, LOCAL}, " ")
		_, err = ws.Write([]byte(session))
		if err == nil {
			ope = &Operation{
				tegaId:     tegaId,
				host:       host,
				port:       port,
				version:    -1,
				path:       "",
				ws:         ws,
				subscriber: subscriber,
			}
		}
	}

	go ope.wsReader()

	return ope, err
}

func (ope *Operation) wsReader() {
	var err error
	for {
		var notify string
		err = nil
		err = websocket.Message.Receive(ope.ws, &notify)
		if err == nil {
			msg := strings.Split(notify, "\n")[1]
			n := &[]Notify{}
			err = json.Unmarshal([]byte(msg), n)
			if err == nil {
				ope.subscriber.OnNotify(n)
			}
		}
		if err != nil {
			log.Fatal(err)
		}
	}
}

func (ope *Operation) urlEncode() *string {
	values := url.Values{}
	if ope.version >= 0 {
		version := strconv.Itoa(ope.version)
		values.Add("version", version)
	}
	values.Add("tega_id", ope.tegaId)
	path := strings.Replace(ope.path, ".", "/", -1)
	url := "http://" + ope.host + ":" + strconv.Itoa(ope.port) + "/" + path + "/?" + values.Encode()
	return &url
}

// CRUD read operation
func (ope *Operation) Get(path string, instance interface{}) error {
	ope.path = path
	url := ope.urlEncode()
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

// CRUD create/update operation
func (ope *Operation) Put(path string, instance interface{}) error {
	ope.path = path
	url := ope.urlEncode()
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

// CRUD delete operation
func (ope *Operation) Delete(path string) error {
	ope.path = path
	url := ope.urlEncode()
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
