from .Parsers import SensorParser, StationsParser, IndexParser
from .Data import Data
from copy import deepcopy
import asyncio
import aiohttp


class GiosParser:
    """
    Main parser class to get air quality data from GIOS API.
    """

    def __init__(self, url: str = "", max_concurrent: int = 10):
        """
        :param url: base API link
        :param max_concurrent: max number of requests at the same time
        """
        self.max_concurrent = max_concurrent
        self._station_parser = StationsParser(url)
        self._sensor_parser = SensorParser(url)
        self._index_parser = IndexParser(url)
        self._data: dict[str, list[Data]] = {}

    async def _fetch_station_data(self, session: aiohttp.ClientSession, station: dict, semaphore: asyncio.Semaphore) -> Data:
        """
        Get sensors and index for one station.
        :param session: active web session
        :param station: dict with station info
        :param semaphore: limit for parallel requests
        :return: Data object for this station
        """
        sensors, aq_index = await asyncio.gather(
            self._sensor_parser.fetch(session, station["station_id"], semaphore=semaphore),
            self._index_parser.fetch(session, station["station_id"], semaphore=semaphore)
        )
        return Data(station, sensors, aq_index)

    async def _fetch_async(self, wojewodztwo: str | None = None) -> dict[str, list[Data]]:
        """
        Download data for all stations or one region.
        :param wojewodztwo: region name to filter (optional)
        :return: dict with region names and lists of Data objects
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async with aiohttp.ClientSession() as session:
            all_stations = await self._station_parser.fetch(session, semaphore=semaphore)

            if wojewodztwo:
                target = wojewodztwo.strip().casefold()
                all_stations = [
                    st for st in all_stations
                    if st["wojewodztwo"].casefold() == target
                ]

            grouped: dict[str, list[dict]] = {}
            for st in all_stations:
                woj = st["wojewodztwo"]
                if woj not in grouped:
                    grouped[woj] = []
                grouped[woj].append(st)

            result: dict[str, list[Data]] = {}
            for woj, stations_in_woj in grouped.items():
                tasks = [self._fetch_station_data(session, st, semaphore=semaphore) for st in stations_in_woj]
                result[woj] = list(await asyncio.gather(*tasks))

        if wojewodztwo is None:
            self._data = result
        else:
            self._data.update(result)

        return self.get_data()

    def fetch_voivodeship(self, wojewodztwo: str) -> list[Data]:
        """
        Get data for all stations in one region.
        :param wojewodztwo: region name
        :return: list of Data objects
        """
        data = asyncio.run(self._fetch_async(wojewodztwo=wojewodztwo))
        target = wojewodztwo.strip().casefold()
        for woj, stations in data.items():
            if woj.casefold() == target:
                return stations
        return []

    def fetch_all(self) -> dict[str, list[Data]]:
        """
        Get data for all stations in Poland.
        :return: dict with regions and lists of Data objects
        """
        return asyncio.run(self._fetch_async())

    def get_data(self) -> dict[str, list[Data]]:
        """
        Get a safe copy of saved data.
        :return: dict with regions and lists of Data objects
        """
        return deepcopy(self._data)