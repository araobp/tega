import tega.driver as driver
import person_pb2

if __name__ == '__main__':

    driver = driver.Driver(tega_id="driver_test")

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
    print(person)

