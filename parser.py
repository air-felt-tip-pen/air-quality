from abc import ABC, abstractmethod
import requests
from copy import deepcopy

from psutil import sensors_battery


class Data:
    """
    data from station and him sensors
    """
    _AIR_QUALITY_THRESHOLDS = {
        "PM10": [
            (20.0, "Bardzo dobry"),
            (50.0, "Dobry"),
            (80.0, "Umiarkowany"),
            (110.0, "Dostateczny"),
            (150.0, "Zły"),
        ],
        "PM2.5": [
            (13.0, "Bardzo dobry"),
            (35.0, "Dobry"),
            (55.0, "Umiarkowany"),
            (75.0, "Dostateczny"),
            (110.0, "Zły"),
        ],
        "O3": [
            (70.0, "Bardzo dobry"),
            (120.0, "Dobry"),
            (150.0, "Umiarkowany"),
            (180.0, "Dostateczny"),
            (240.0, "Zły"),
        ],
        "NO2": [
            (40.0, "Bardzo dobry"),
            (100.0, "Dobry"),
            (150.0, "Umiarkowany"),
            (230.0, "Dostateczny"),
            (400.0, "Zły"),
        ],
        "SO2": [
            (50.0, "Bardzo dobry"),
            (100.0, "Dobry"),
            (200.0, "Umiarkowany"),
            (350.0, "Dostateczny"),
            (500.0, "Zły"),
        ],
    }

    _INDEX_RANK = {
        "Bardzo dobry": 1,
        "Dobry": 2,
        "Umiarkowany": 3,
        "Dostateczny": 4,
        "Zły": 5,
        "Bardzo zły": 6,
    }

    def __init__(self, station: dict, sensors: list[dict]):
        """
        :param station: dict with station information
        :param sensors: list with dict sensor information
        """
        self._city_id = station.get("city_id")
        self._station_id = station.get("station_id")
        self._powiat = station.get("powiat")
        self._coords = station.get("coord")

        self.sensor = {
            s['Kod']: s
            for s in sensors if s.get('Kod') is not None
        }


    def calc_air_quality(self, code: str, value: int | float) -> str:
        """
        :param code: Code for substances in the air
        :param value: Their volume per cubic metre
        :return: Air quality string or 'No info'
        """
        if value is None or code not in self._AIR_QUALITY_THRESHOLDS:
            return "No info"
        for v, name in self._AIR_QUALITY_THRESHOLDS[code]:
            if value <= v:
                return name
        return "Bardzo zły"

    def get_air_quality(self, code: str) -> str:
        """
        :param code: code for substances in the air
        :return: Air quality string or 'No info'
        """
        sensor_info = self.sensor.get(code)
        if not sensor_info:
            return "No info"
        return self.calc_air_quality(code, sensor_info.get("Value"))

    def get_overall_station_index(self) -> str:
        """
        :return:  Air quality string or 'No info'
        """
        worst_rank = 0
        worst_label = "No info"

        for code in self._AIR_QUALITY_THRESHOLDS.keys():
            if code in self.sensor:
                val = self.sensor[code].get("Value")
                label = self.calc_air_quality(code, val)

                if label in self._INDEX_RANK:
                    rank = self._INDEX_RANK[label]
                    if rank > worst_rank:
                        worst_rank = rank
                        worst_label = label
        return worst_label

    def get_full_status(self):
        individual = dict()
        for code, data in self.sensor.items():
            individual[code] = {
                "name": data.get("Name"),
                "value": data.get("Value"),
                "index": self.calc_air_quality(code, data.get("Value"))
            }
        return {
            'overall_index': self.get_overall_station_index(),
            'sensors': individual
        }

    @property
    def city_id(self):
        return self._city_id

    @property
    def station_id(self):
        return self._station_id

    @property
    def powiat(self):
        return self._powiat

    @property
    def coords(self):
        return self._coords

    def __str__(self) -> str:
        return f"{self.city_id} {self._station_id} {self._powiat} {self.sensor.keys()}"

    def __repr__(self) -> str:
        return self.__str__()


class BaseParser(ABC):
    def __init__(self, url: str = '', session: requests.Session | None = None):
        """
        :param url: Base URL of GIOŚ API (defaults to v1 REST API)
        :param session: HTTP session to use for requests
        """
        if not isinstance(url, str):
            raise TypeError("Url must be a string")
        if not url.startswith("https://") and url:
            raise ValueError("Url must start with 'https://'")

        self._URL = url or "https://api.gios.gov.pl/pjp-api/v1/rest"
        self._session = session or requests.Session()

    def _make_request(self, endpoint: str = '', timeout: tuple[int, int] = (5, 30)) -> requests.Response:
        """
        :param endpoint: API endpoint path (e.g. '/station/findAll')
        :param timeout: tuple ((connect_timeout, read_timeout))
        :return: requests.Response object
        """
        url = f"{self._URL}/{endpoint.lstrip('/')}"
        response = self._session.get(url, timeout=timeout)
        response.raise_for_status()
        return response

    @property
    def url(self) -> str:
        return self._URL

    @abstractmethod
    def parse(self, key, value) -> list:
        """
        :param key: Key to filter by
        :param value: Target value to match
        :return: list of matching elements
        """
        pass


class StationsParser(BaseParser):
    def __init__(self, url: str = '', session: requests.Session | None = None):
        super().__init__(url, session)
        self._stations: list[dict] = []

    def fetch(self) -> list[dict]:
        """Method to fetch all stations"""

        try:
            stations_resp = self._make_request("/station/findAll")
            raw_stations = stations_resp.json().get("Lista stacji pomiarowych", [])

            self._stations = [{
                'city_id': i.get("Identyfikator miasta"),
                'station_id': i.get("Identyfikator stacji"),
                'powiat': i.get("Powiat"),
                'coord': (i.get('WGS84 λ E'), i.get('WGS84 φ N')),
            } for i in raw_stations]

        except (requests.RequestException, KeyError) as e:
            self._stations = []
            raise ConnectionError(f"Error fetch station: {e}") from e

        return self._stations

    def parse(self, key, value) -> list:
        return [s for s in self._stations if s.get(key) == value]

    @property
    def stations(self) -> list[dict]:
        return deepcopy(self._stations)





class SensorParser(BaseParser):
    def __init__(self, url: str = '', session: requests.Session | None = None):
        super().__init__(url, session)
        self._sensor: list[dict] = []

    def fetch(self, station_id: str | int) -> list[dict]:
        """Gets latest measurement values for a given station ID.
        :param station_id: ID of the target station
        :return: list of dicts containing sensor information and latest measurement
        """
        sensors_return = []
        try:
            sensors_resp = self._make_request(f"/station/sensors/{station_id}")
            sensors = sensors_resp.json().get("Lista stanowisk pomiarowych dla podanej stacji", [])

            for s in sensors:
                sensor_id = s.get('Identyfikator stanowiska')
                try:
                    data_resp = self._make_request(f"/data/getData/{sensor_id}")
                    history = data_resp.json().get("Lista danych pomiarowych", [])
                    latest: dict | None = next((m for m in history if m.get("Wartość") is not None), None)

                    data = {
                        'Name': s.get("Wskaźnik"),
                        'Kod': s.get("Wskaźnik - kod"),
                        'Value': latest.get('Wartość') if latest else None,
                        'Data': latest.get('Data') if latest else None
                    }
                except requests.RequestException:
                    data = {
                        'Name': s.get("Wskaźnik"),
                        'Kod': s.get("Wskaźnik - kod"),
                        'Value': None,
                        'Data': None
                    }
                sensors_return.append(data)
        except requests.RequestException:
            sensors_return = []

        self._sensor = sensors_return
        return self._sensor

    def parse(self, key, value) -> list[dict]:
        return [s for s in self._sensor if s.get(key) == value]

    @property
    def sensors(self) -> list:
        return deepcopy(self._sensor)


class GiosParser:
    def __init__(self, url: str = ''):
        """
        :param url: Base URL of GIOŚ API
        """
        self._url = url
        self._session = requests.Session()
        self._data: list[Data] = []

    def fetch(self, limit: int | None = None) -> list[Data]:
        """
        fetches stations and their corresponding sensors to construct Data objects.
        :param limit: limit count of stations
        :return: list of Data objects
        """
        stations_parser = StationsParser(self._url, session=self._session)
        stations = stations_parser.fetch()

        if limit is not None:
            stations = stations[:limit]

        sensor_parser = SensorParser(self._url, session=self._session)
        result = []

        for station in stations:
            sensors_list = sensor_parser.fetch(station['station_id'])
            result.append(Data(station, sensors_list))

        self._data = result
        return self._data


    def show(self) -> list[Data]:
        """
        :return: list of Data objects representing all processed stations
        """
        return self._data