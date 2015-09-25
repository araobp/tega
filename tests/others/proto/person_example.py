#!./do_test.sh
#
# This is an example of t7 - protocol buffer concatination.

from tega.tree import * 
import address_book_pb2

# Create test (protocol buffer)
addressbook = address_book_pb2.AddressBook()

person = addressbook.person.add()
person.id = 1234
person.name = "John Doe"
person.email = "jdoe@example.com"
phone = person.phone.add()
phone.number = "555-4321"
phone.type = address_book_pb2.Person.HOME

person2 = addressbook.person.add()
person2.id = 4321
person2.name = "Alexanderplatz1999"
person2.email = "alexanderplatz1999@gmail.com"
phone2 = person2.phone.add()
phone2.number = "666-4321"
phone2.type = address_book_pb2.Person.MOBILE

print("--- protocol buffer ---")
print(addressbook) 

print("--- protocol buffer ---")
for p in addressbook.person:
    print(p) 

print("--- protocol buffer (SerializeToString()) ---")
print(addressbook.SerializeToString())

print("--- tree7047/protocol_buffer (iteritems) ---")
ab = Cont('addressbook')
ab.id[1234]=person
ab.id[4321]=person2
for k,v in ab.id.items():
    print(v) 


print("--- tree7047/protocol_buffer (walk) ---")
print(ab.walk_(True))

print("--- tree7047/protocol_buffer (deepcopy) ---")
ab2 = ab.deepcopy_()
print(ab2.walk_(True))


# This is how Cont class creates a similar object to the above

ab = Cont('addressbook') 

person = ab(id=1234)
person.name = "John Doe"
person.email = "jdoe@example.com"
phone = person.phone
phone.number = "555-4321"
phone.type = "HOME" 

person2 = ab(id=4321)
person2.name = "Alexanderplatz1999"
person2.email = "alexanderplatz1999@gmail.com"
phone2 = person2.phone
phone2.number = "666-4321"
phone2.type = "MOBILE"

print("--- tree7047 ---")
print(ab)
