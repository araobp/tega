package driver

import (
	"bytes"
	"encoding/json"
	"io/ioutil"
	"log"
	"net/http"
	"net/url"
	"strconv"
	"strings"
)

const (
	TEGA_ID = "anonymous"
	HOST    = "localhost"
	PORT    = 8888
)

type Operation struct {
	TegaId   string
	Host     string
	Port     int
	path     string
	version  int
	instance []interface{}
}

func NewOperation() *Operation {
	return &Operation{
		TegaId:   TEGA_ID,
		Host:     HOST,
		Port:     PORT,
		instance: nil,
		path:     "",
		version:  -1,
	}
}

func (ope *Operation) urlEncode() *string {
	values := url.Values{}
	if ope.instance != nil {
		jsonValue, err := json.Marshal(ope.instance)
		if err == nil {
			values.Add("instance", bytes.NewBuffer(jsonValue).String())
		} else {
			log.Print(err)
		}
	}
	if ope.version >= 0 {
		version := strconv.Itoa(ope.version)
		values.Add("version", version)
	}
	values.Add("tega_id", ope.TegaId)
	path := strings.Replace(ope.path, ".", "/", -1)
	url := "http://" + ope.Host + ":" + strconv.Itoa(ope.Port) + "/" + path + "/?" + values.Encode()
	return &url
}

func (ope *Operation) Get(path string, version int) string {
	ope.path = path
	ope.version = version
	url := ope.urlEncode()
	resp, err := http.Get(*url)
	defer resp.Body.Close()
	var body []byte
	if err != nil {
		log.Print(err)
	} else {
		body, err = ioutil.ReadAll(resp.Body)
		if err != nil {
			log.Print(err)
		}
	}
	return string(body)
}
