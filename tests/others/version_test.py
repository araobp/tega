#!/usr/bin/env python3.4

from tega.tree import * 

b = Cont('b')
b.c(id=1, group='alice in wonderland').list = ['alice', 'bob']
b.c(id=1, group='alice in wonderland').dict = {'colors':['green', 'red']} 
b.c(id=2, group='beatles').list = ['john', 'paul', 'geroge', 'ringo']
b.c(id=2, group='beatles').dict = {'colors':['blue', 'purple']}

print(b.walk_(internal=True))

bb = b.copy_()

print('')
print(bb.walk_(internal=True))



