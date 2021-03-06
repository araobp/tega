package driver

import (
	"errors"
	"log"
	"testing"
	"time"
)

type A struct {
	B B `json:"b"`
}

type B struct {
	C string `json:"c"`
}

type Self struct {
}

func (r *Self) OnInit() {
	log.Print("OnInit()")
}

func (r *Self) OnNotify(v *[]Notification) {
	log.Print("Notify: %s", *v)
	for _, i := range *v {
		log.Printf("Notify.Instance: %s", i.Instance.(string))
	}
}

func (r *Self) OnMessage(channel string, tegaId string, v *Message) {
	log.Printf("Channel: %s, TegaId: %s, Message: %s", channel, tegaId, *v)
}

var self *Self
var ope *Operation
var ope2 *Operation

func TestMain(t *testing.T) {
	self = &Self{}
	ope, _ = NewOperation("", "", 0, self, GLOBAL)
	ope2, _ = NewOperation("anonymous2", "", 0, self, LOCAL) 
	ope.Delete("a")
	body := "test"
	ope.Put("a.b.c", &body)
}

func TestGet(t *testing.T) {
	var body interface{}
	ope.Get("a", &body)
	log.Print(body)
	ope.Get("a.b", &body)
	log.Print(body)
	ope.Get("a.b.c", &body)
	log.Print(body)
	a := A{}
	ope.Get("a", &a)
	log.Print(a)
	log.Print(a.B)
	log.Print(a.B.C)
}

func TestPut(t *testing.T) {
	var body string = "test2"
	err := ope.Put("a.b.c", &body)
	if err != nil {
		log.Print(err)
	}
	body2 := A{
		B: B{
			C: "test3",
		},
	}
	err = ope.Put("a", &body2)
	if err != nil {
		log.Print(err)
	}
}

func TestSubscribe(t *testing.T) {
	err := ope.Subscribe("a", LOCAL)
	if err != nil {
		log.Print(err)
	}
	time.Sleep(1 * time.Second)
	var body string = "test4"
	err = ope2.Put("a.b.c", &body)
	if err != nil {
		log.Print(err)
	}
	time.Sleep(1 * time.Second)
	body = "test5"
	err = ope2.Put("a.b.x", &body)
	if err != nil {
		log.Print(err)
	}
	time.Sleep(1 * time.Second)
}

func TestPubSub(t *testing.T) {
	ope.Subscribe("channels.ch1", LOCAL)
	ope.Subscribe("channels.ch2", LOCAL)
	ope.Subscribe("channels", LOCAL)
	time.Sleep(1 * time.Second)
	msg := Message{Msg: "Good Morning!"}
	ope2.Publish("channels.ch1", &msg)
	time.Sleep(1 * time.Second)
	msg2 := Message{Msg: "Guten Morgen!"}
	ope2.Publish("channels.ch2", &msg2)
	time.Sleep(1 * time.Second)
	msg3 := Message{Msg: "Bye!"}
	ope2.Publish("channels", &msg3)
	time.Sleep(1 * time.Second)
}

func TestRpc(t *testing.T) {
	ope.RegisterRpc("test.func.max", max)
	time.Sleep(10 * time.Second)
}

func max(argsKwargs ArgsKwargs) (Result, error) {
	args := argsKwargs.Args
	v1 := args[0].(float64)
	v2 := args[1].(float64)
	if v1 >= v2 {
		return Result{Res: v1}, errors.New("OK")
	} else {
		return Result{Res: v2}, errors.New("OK")
	}
}
