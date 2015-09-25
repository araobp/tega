Protocol Buffer
---------------
addressbook = address_book_pb2.AddressBook()
person = addressbook.person.add()
person.id = 1234
person.name = "John Doe"
person.email = "jdoe@example.com"
phone = person.phone.add()
phone.number = "555-4321"
phone.type = address_book_pb2.Person.HOME


tega
----
addressbook = Cont('addressbook') 
person = addressbook(id=1234)
person.name = "John Doe"
person.email = "jdoe@example.com"
phone = person.phone[0]
phone.number = "555-4321"
phone.type = "HOME" 

