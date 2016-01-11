##Tega driver for golang

Note: Tega driver for Pytyon is [here](../tega/driver).

```
 [tega server] <----- CRUD/DCN(HTTP/WebSocket) ------> [driver for golang]
```

##Preparation
Append the following line to your $HOME/.bashrc:
```
export PYTHONPATH=$GOPATH/src/github.com/araobp/tega:$PYTHONPATH
```
Then
```
$ source ~/.bashrc
```

##Test
[Step1] Start tega db
```
$ ./server
```

[Step2] Test the driver
```
$ go test
```
##Test data
- [minimal commit log](./var)
