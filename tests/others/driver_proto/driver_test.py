import tega.driver as driver
from tega.tree import Cont

import person_pb2

if __name__ == '__main__':

    ### Tega driver ###
    driver = driver.Driver(tega_id="driver_test")
    

    ### protobuf ###

    address_book = person_pb2.AddressBook()

    person = address_book.person.add()
    person.id = 1234
    person.name = "John Doe"
    person.email = "jdoe@example.com"
    phone = person.phone.add()
    phone.number = "555-4321"
    phone.type = person_pb2.Person.HOME

    driver.put_proto(path="address_book", message=address_book)

    person = driver.get_proto(path="address_book", template=person_pb2.AddressBook())

    ### Cont ###

    ab2 = Cont("address_book2")
    person = ab2.person
    person.id = 1234
    person.name = "John Doe"
    person.email = "jdoe@example.com"
    person.phone.number = "555-4321"
    person.phone.type = "HOME"

    driver.put(person)

    persons = driver.get(path="address_book2", python_dict=True)

