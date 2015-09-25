#!/usr/bin/env python3.4

from tega.tree import * 

a = Cont('a')

# a list of oids
c = [a.b, a.c]

c[0].i = 1
c[1].i = 2

print(a.walk_())

print('')

b = Cont('b')
b.c(id=1, group='alice in wonderland').list = ['alice', 'bob']
b.c(id=1, group='beatles').list = ['john', 'paul', 'geroge', 'ringo']
print(b.c(id=1, group='alice in wonderland').list[0])
print(b.c(id=1, group='beatles').list[1])
print('')
print(b.c(id=1, group='beatles').list[0])
print(b.c(id=1, group='beatles').list[1])
print(b.c(id=1, group='beatles').list[2])
print(b.c(id=1, group='beatles').list[3])
print('')
print(b.walk_())

print('')
for k in b.c:
    l = b.c(**k).list
    for person in l:
        print(person)

for k,v in b.c.items():
    print(k)
    print(v) 

