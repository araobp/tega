#Guideline

##Modelling
If you use this database for DevOps, three-tier tree structure is ideal from an implementational point of view.
```
config-<router>.<service_module or rpc>.<args/kwargs>
operatoinal-<router>.<service_module>.<args/kwargs>
```

