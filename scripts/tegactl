#!/usr/bin/env python3.4

from tega.driver import Driver

import json 
import sys

if __name__ == '__main__':
    ope = sys.argv[1]
    path = sys.argv[2]
    instance = None
    if len(sys.argv) > 3:
        instance = sys.argv[3]

    d = Driver()
    if ope == "get":
        value = json.dumps(d.get(path=path, json_format=True))
        print(value)
    elif ope == "delete":
        d.delete(path=path)
    elif ope == "put":
        pass



