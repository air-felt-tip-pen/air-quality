from abc import ABC, abstractmethod
from copy import deepcopy
import asyncio
import aiohttp
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

class BaseParser(ABC):
    def __init__(self, url: str = "", max_concurrent: int = 10):
        if not isinstance(url, str):
            raise TypeError("Url must be a string")
        if url and not url.startswith("https://"):
            raise ValueError("Url must start with 'https://'")

        self._URL = (url or "https://api.gios.gov.pl/pjp-api/v1/rest").rstrip("/")
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def _make_request(
            self,
            session: aiohttp.ClientSession,
            endpoint: str,
            timeout: int = 15
    ) -> dict | None:
        url = f"{self._URL}/{endpoint.lstrip('/')}"
        async with self._semaphore:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                    response.raise_for_status()
                    return await response.json()
            except (aiohttp.ClientError, asyncio.TimeoutError):
                return None

    @property
    def url(self) -> str:
        return self._URL

    @abstractmethod
    async def fetch(self, session: aiohttp.ClientSession):
        pass



class StationsParser(BaseParser):
    @staticmethod
    def _parse_coords(lat_raw, lon_raw) -> dict[str, float] | None:
        if lat_raw is None or lon_raw is None:
            return None
        try:
            return {"lat": float(lat_raw), "lon": float(lon_raw)}
        except (ValueError, TypeError):
            return None

    async def fetch(self, session: aiohttp.ClientSession) -> list[dict]:
        all_raw_stations = []
        page = 0
        size = 500
        while True:
            data = await self._make_request(session, f"/station/findAll?page={page}&size={size}")
            if not data:
                if page == 0:
                    raise ConnectionError("Failed to fetch stations from GIOŚ API")
                break

            raw_stations = data.get("Lista stacji pomiarowych", [])
            if not raw_stations:
                break

            all_raw_stations.extend(raw_stations)

            total_pages = data.get("totalPages")
            if total_pages is not None and page + 1 >= total_pages:
                break
            if len(raw_stations) < size:
                break

            page += 1

        return [
            {
                "city_id": i.get("Identyfikator miasta"),
                "station_id": i.get("Identyfikator stacji"),
                "station_name": i.get("Nazwa stacji"),
                "powiat": i.get("Powiat") or "Inne",
                "wojewodztwo": i.get("Województwo") or "INNE",
                "coords": self._parse_coords(i.get("WGS84 φ N"), i.get("WGS84 λ E")),
            }
            for i in all_raw_stations
        ]

class SensorParser(BaseParser):

    _WARSAW_TIMEZONE = ZoneInfo('Europe/Warsaw')

    @classmethod
    def _is_data_stale(cls, date_str: str | None, max_age_hours: int = 3) -> bool:
        if not date_str:
            return True
        try:
            data = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=cls._WARSAW_TIMEZONE)
            now = datetime.now(cls._WARSAW_TIMEZONE)
            return (now - data) > timedelta(hours=max_age_hours)
        except ValueError:
            return True

    async def _fetch_single_sensor(self, session: aiohttp.ClientSession, sensor_meta: dict) -> dict:
        sensor_id = sensor_meta.get("Identyfikator stanowiska")
        data = await self._make_request(session, f"/data/getData/{sensor_id}")

        latest = None
        if data:
            history = data.get("Lista danych pomiarowych", [])
            valid_data = [m for m in history if m.get("Wartość") is not None]
            latest = max(valid_data, key=lambda m: m.get("Data") or "", default=None)

        date_str = latest.get("Data") if latest else None

        return {
            "sensor_id": sensor_id,
            "Name": sensor_meta.get("Wskaźnik"),
            "Kod": sensor_meta.get("Wskaźnik - kod"),
            "Value": latest.get("Wartość") if latest else None,
            "Data": date_str,
            "is_stale": self._is_data_stale(date_str),
        }

    async def fetch(self, session: aiohttp.ClientSession, station_id: str | int) -> list[dict]:
        data = await self._make_request(session, f"/station/sensors/{station_id}")
        if not data:
            return []

        sensors = data.get("Lista stanowisk pomiarowych dla podanej stacji", [])
        tasks = [self._fetch_single_sensor(session, s) for s in sensors]
        return list(await asyncio.gather(*tasks))



class IndexParser(BaseParser):
    _POLLUTANTS = ("PM10", "PM2.5", "O3", "NO2", "SO2")


    @staticmethod
    def _get_pollutant_index(raw_index: dict[str, str], code: str) -> str:
        keys = (
            f"Nazwa kategorii indeksu dla wskaźnika {code}"
            f"Nazwa kategorii indeksu dla wskażnika {code}"
        )
        for key in keys:
            value = raw_index.get(key)
            if value:
                return value
        return "Brak indeksu"

    async def fetch(self, session: aiohttp.ClientSession, station_id: str | int) -> dict:
        data = await self._make_request(session, f"/aqindex/getIndex/{station_id}")
        if not isinstance(data, dict):
            return {"overall_index": "Brak indeksu", "calc_date": None, "pollutants": {}}

        raw_index = data.get("AqIndex") or data

        pollutants = {
            code: self._get_pollutant_index(raw_index, code)
            for code in self._POLLUTANTS
        }

        return {
            "overall_index": raw_index.get("Nazwa kategorii indeksu") or "Brak indeksu",
            "calc_date": raw_index.get("Data wykonania obliczeń indeksu"),
            "pollutants": pollutants,
        }