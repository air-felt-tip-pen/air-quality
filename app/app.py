import json
from time import perf_counter
from parsers.GiosParser import GiosParser
from normalizers.DataNormalizer import DataNormalizer
from analytics.analizer import AirQualityAnalyzer
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
    # pprint(data["LUBELSKIE"][:3])
    print("\n\n")
    # pprint(data["LUBELSKIE"][0].sensor)
    # print("\n\n")

    normalizer = DataNormalizer()
    clean_data = normalizer.clean(data)

    print(f"Start dumping to JSON...")
    with open("data/data.json", "w", encoding="utf-8") as outfile:
        json.dump(
            clean_data,
            outfile,
            indent=4,
            ensure_ascii=False
        )

    analyzer = AirQualityAnalyzer()
    analyzer.analyze(clean_data)



if __name__ == "__main__":
    main()