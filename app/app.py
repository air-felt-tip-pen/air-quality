import json
from time import perf_counter
from parsers.GiosParser import GiosParser
from normalizers.DataNormalizer import DataNormalizer
from pprint import pprint

def main():
    parser = GiosParser()

    print("Start parsing...")
    start = perf_counter()
    parser.fetch_all()
    data = parser.get_data()
    parse_time = perf_counter() - start
    print(f"Parsing finished in {parse_time:.2f}s.")

    print()
    print(len(data))
    pprint(data["LUBELSKIE"][:3])
    print("\n\n")
    pprint(data["LUBELSKIE"][0].sensor)
    print("\n\n")

    normalizer = DataNormalizer()
    clean_data = normalizer.clean(data)

    print(f"Start dumping to JSON...")
    try:
        with open("data/data.json", "w", encoding="utf-8") as outfile:
            json.dump(
                clean_data,
                outfile,
                indent=4,
                ensure_ascii=False
            )
    except:
        with open("app/data/data.json", "w", encoding="utf-8") as outfile:
            json.dump(
                clean_data,
                outfile,
                indent=4,
                ensure_ascii=False
            )

    total_time = perf_counter() - start
    print(f"Done! Total execution time: {total_time:.2f}s")
    pprint(parser.fetch_voivodeship("LUBELSKIE"))


if __name__ == "__main__":
    main()