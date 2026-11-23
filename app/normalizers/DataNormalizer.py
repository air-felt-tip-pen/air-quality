from datetime import datetime
import math
import re
from typing import Any


class DataNormalizer:
    """
    Normalizes, validates, and filters air quality data parsed from GIOS API.
    """

    INDEX_RANK: dict[str, int] = {
        "Bardzo dobry": 1,
        "Dobry": 2,
        "Umiarkowany": 3,
        "Dostateczny": 4,
        "Zły": 5,
        "Bardzo zły": 6,
    }
    _INDEX_LOOKUP = {k.casefold(): k for k in INDEX_RANK}
    _PL_LAT = (49.0, 55.0)
    _PL_LON = (14.0, 24.5)

    def __init__(
        self,
        drop_empty_stations: bool = True,
        require_sensors: bool = False,
        require_coords: bool = False,
        drop_empty_regions: bool = True,
        max_sensor_age_hours: int | None = None,
    ):
        """
        :param drop_empty_stations: remove stations with no valid sensors AND 'Brak indeksu'
        :param require_sensors: remove stations that have 0 valid sensors (even if overall_index exists)
        :param require_coords: remove stations without valid Polish coordinates
        :param drop_empty_regions: remove voivodeships that have 0 stations after filtering
        :param max_sensor_age_hours: optional max age in hours for sensor readings (None = rely on is_stale)
        """
        self.drop_empty_stations = drop_empty_stations
        self.require_sensors = require_sensors
        self.require_coords = require_coords
        self.drop_empty_regions = drop_empty_regions
        self.max_sensor_age_hours = max_sensor_age_hours

    def clean(self, data: dict[str, list[Any]]) -> dict[str, list[dict]]:
        """
        Clean and normalize all voivodeships and their stations.
        Accepts dicts containing Data objects or already serialized station dicts.
        """
        if not isinstance(data, dict):
            return {}

        result: dict[str, list[dict]] = {}
        for raw_region in sorted(data):
            region = self._text(raw_region).upper()
            if not region:
                continue

            seen_ids: set[int] = set()
            stations: list[dict] = []

            for raw_st in data.get(raw_region) or []:
                st = self._normalize_station(raw_st, region)
                if st and st["station_id"] not in seen_ids:
                    seen_ids.add(st["station_id"])
                    stations.append(st)

            stations.sort(key=lambda s: s["station_name"].casefold())
            if stations or not self.drop_empty_regions:
                result[region] = stations

        return result

    def _normalize_station(self, station: Any, fallback_region: str) -> dict | None:
        raw = station.to_dict() if hasattr(station, "to_dict") else station
        if not isinstance(raw, dict):
            return None

        station_id = self._num(raw.get("station_id"), int)
        name = re.sub(
            r"\b(ul|al|os|pl)\.(?=[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż])",
            r"\1. ",
            self._text(raw.get("station_name")),
            flags=re.IGNORECASE,
        )
        if station_id is None or not name:
            return None

        coords = self._normalize_coords(raw.get("coords"))
        if self.require_coords and not coords:
            return None

        overall_index = self._index_label(raw.get("overall_index"))
        has_index = overall_index != "Brak indeksu"
        calc_dt = self._parse_dt(raw.get("index_calc_date")) if has_index else None
        sensors = self._normalize_sensors(raw.get("sensors"))

        if (self.require_sensors and not sensors) or (
            self.drop_empty_stations and not sensors and not has_index
        ):
            return None

        return {
            "city_id": self._num(raw.get("city_id"), int),
            "station_id": station_id,
            "station_name": name,
            "powiat": self._text(raw.get("powiat")) or None,
            "wojewodztwo": self._text(raw.get("wojewodztwo")).upper() or fallback_region,
            "coords": coords,
            "overall_index": overall_index,
            "index_rank": self.INDEX_RANK.get(overall_index),
            "index_calc_date": calc_dt.strftime("%Y-%m-%d %H:%M:%S") if calc_dt else None,
            "sensors_count": len(sensors),
            "sensors": sensors,
        }

    def _normalize_sensors(self, raw_sensors: Any) -> dict[str, dict]:
        if not isinstance(raw_sensors, dict):
            return {}

        clean: dict[str, dict] = {}
        now = datetime.now()
        items = sorted(
            raw_sensors.items(),
            key=lambda x: str((x[1] or {}).get("code") or (x[1] or {}).get("Kod") or ""),
        )

        for raw_key, s in items:
            if not isinstance(s, dict) or s.get("is_stale"):
                continue

            val = self._num(s.get("value") if "value" in s else s.get("Value"), float)
            code = self._text(s.get("code") or s.get("Kod"))
            dt = self._parse_dt(s.get("date") if "date" in s else s.get("Data"))
            sensor_id = self._num(s.get("sensor_id") or raw_key, int)

            if val is None or val < 0 or not code or not dt or sensor_id is None:
                continue
            if self.max_sensor_age_hours is not None and (now - dt).total_seconds() > self.max_sensor_age_hours * 3600:
                continue

            idx = self._index_label(s.get("index"))
            clean[str(sensor_id)] = {
                "sensor_id": sensor_id,
                "code": code,
                "name": self._text(s.get("name") or s.get("Name")) or code,
                "value": round(val, 3),
                "date": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "index": idx,
                "index_rank": self.INDEX_RANK.get(idx),
            }

        return clean

    def _normalize_coords(self, coords: Any) -> dict[str, float] | None:
        if not isinstance(coords, dict):
            return None
        lat = self._num(coords.get("lat"), float)
        lon = self._num(coords.get("lon"), float)
        if (
            lat is not None
            and lon is not None
            and self._PL_LAT[0] <= lat <= self._PL_LAT[1]
            and self._PL_LON[0] <= lon <= self._PL_LON[1]
        ):
            return {"lat": round(lat, 6), "lon": round(lon, 6)}
        return None

    def _index_label(self, label: Any) -> str:
        return self._INDEX_LOOKUP.get(self._text(label).casefold(), "Brak indeksu")

    @staticmethod
    def _text(val: Any) -> str:
        return re.sub(r"\s+", " ", str(val).strip()) if val is not None else ""

    @staticmethod
    def _num(val: Any, cast: type[int] | type[float]) -> Any:
        if val is None or isinstance(val, bool):
            return None
        try:
            res = cast(val)
            return res if math.isfinite(res) else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_dt(val: Any) -> datetime | None:
        if not isinstance(val, str) or len(val.strip()) < 16:
            return None
        try:
            return datetime.fromisoformat(val.strip())
        except ValueError:
            return None