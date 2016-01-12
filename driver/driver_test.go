package driver

import (
	"log"
	"testing"
)

type A struct {
	B B `json:"b"`
}

type B struct {
	C string `json:"c"`
}

type Self struct {
}

func (r *Self) OnNotify(v interface{}) {
	log.Print(v)
}

var self *Self
var ope *Operation

func TestMain(t *testing.T) {
	self = &Self{}
	var err error
	ope, err = NewOperation("", "", 0, self)
	if err != nil {
		log.Fatal(err)
	}
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
