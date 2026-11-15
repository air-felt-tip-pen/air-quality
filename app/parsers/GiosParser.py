from .Parsers import SensorParser, StationsParser, IndexParser
from .Data import Data
from copy import deepcopy
import asyncio
import aiohttp

class GiosParser:
    def __init__(self, url: str = "", max_concurrent: int = 10):
        self._station_parser = StationsParser(url, max_concurrent)
        self._sensor_parser = SensorParser(url, max_concurrent)
        self._index_parser = IndexParser(url, max_concurrent)
        self._data: dict[str, list[Data]] = {}

    async def _fetch_station_data(self, session: aiohttp.ClientSession, station: dict) -> Data:
        sensors, aq_index = await asyncio.gather(
            self._sensor_parser.fetch(session, station["station_id"]),
            self._index_parser.fetch(session, station["station_id"]),
        )
        return Data(station, sensors, aq_index)

    async def _fetch_async(self, wojewodztwo: str | None = None) -> dict[str, list[Data]]:
        async with aiohttp.ClientSession() as session:
            all_stations = await self._station_parser.fetch(session)

            if wojewodztwo:
                all_stations = [
                    st for st in all_stations
                    if wojewodztwo.lower() in st["wojewodztwo"].lower()
                ]

            grouped: dict[str, list[dict]] = {}
            for st in all_stations:
                woj = st["wojewodztwo"]
                if woj not in grouped:
                    grouped[woj] = []
                grouped[woj].append(st)

            for woj, stations_in_woj in grouped.items():
                tasks = [self._fetch_station_data(session, st) for st in stations_in_woj]
                self._data[woj] = list(await asyncio.gather(*tasks))

        return self.get_data()

    def fetch_voivodeship(self, wojewodztwo: str) -> list[Data]:
        data = asyncio.run(self._fetch_async(wojewodztwo=wojewodztwo))
        return next(iter(data.values()), [])

    def fetch_all(self) -> dict[str, list[Data]]:
        return asyncio.run(self._fetch_async())

    def get_data(self) -> dict[str, list[Data]]:
        return deepcopy(self._data)