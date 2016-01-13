package driver

import (
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

func (r *Self) OnNotify(v *[]Notify) {
	log.Print("Notify: %s", *v)
	for _, i := range *v {
		log.Printf("Notify.Instance: %s", i.Instance.(string))
	}
}

var self *Self
var ope *Operation
var ope2 *Operation

func TestMain(t *testing.T) {
	self = &Self{}
	ope, _ = NewOperation("", "", 0, self)
	ope2, _ = NewOperation("anonymous2", "", 0, self)
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
