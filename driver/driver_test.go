package driver

import (
	"log"
	"testing"
)

type A struct {
	B B
}

type B struct {
	C string
}

func TestGet(t *testing.T) {
	ope := NewOperation()
	var body interface{}
	ope.Get("a", -1, &body)
	log.Print(body)
	ope.Get("a.b", -1, &body)
	log.Print(body)
	ope.Get("a.b.c", -1, &body)
	log.Print(body)
	a := A{}
	ope.Get("a", -1, &a)
	log.Print(a)
	log.Print(a.B)
	log.Print(a.B.C)
}
