#!/usr/bin/env python3.4

"""
tega's way to create tree-structured data and selialize it into YAML/JSON.

"""

from tega.tree import * 


# Create test 

person = Cont('person')
person.name = "John Doe"
person.email = "jdoe@example.com"
phones = person.phones
phones.mobile = ["555-4321", "123-1234"]
phones.home = ["234-5678"]

person2 = Cont('person2')
person2.name = "Alexanderplatz1999"
person2.email = "alexanderplatz1999@gmail.com"
person2.address.streetaddress = "Alexanderplatz in Berlin, Germany"
phones2 = person2.phones
phones2.home = ["666-4321"]

addressbook = Cont('addressbook')
addressbook(id=1234).person=person
print('""""')
print(addressbook)
print('""""')
addressbook(id=4321).person=person2
print ('------------------------')
print(addressbook.walk_(internal=True))
print ('------------------------')
print(addressbook.dumps_())

# Print test
print ('------------------------')
print(addressbook(id=1234).person.name)
print ('------------------------')
print(addressbook(id=4321).person.name)
print ('------------------------')
print(addressbook(id=4321).walk_())

# Delete test

print ('------------------------')
del addressbook(id=4321).person.address.streetaddress
print(addressbook.walk_())

print ('------------------------')
del addressbook(id=4321).person
print(addressbook.walk_())

print ('------------------------')
addressbook(id=4321).delete_()
print(addressbook.walk_())

