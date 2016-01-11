package driver

import (
	"log"
	"testing"
)

func TestGet(t *testing.T) {
	ope := NewOperation()
	body := ope.Get("a.b.c", -1)
	log.Print(body)
}
