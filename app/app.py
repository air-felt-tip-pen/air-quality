from parsers.GiosParser import GiosParser
from pprint import pprint
from time import perf_counter

if __name__ == "__main__":
    parser = GiosParser()

    start = perf_counter()
    data = parser.fetch_all()

    print(len(data))
    pprint(data["LUBUSKIE"])
    print("\n\n")
    pprint(data["LUBUSKIE"][0].sensor)
    print("\n\n")
    print(f"End: {perf_counter() - start}")