#!/bin/bash

protoc -I=. --python_out=. person.proto
export PYTHONPATH=.:../../..:$PYTHONPATH
python3.4 ./driver_test.py
