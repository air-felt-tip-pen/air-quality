class Data:
    """
    Class for station data, its sensors, and air quality index.
    """
    _INDEX_RANK = {
        "Bardzo dobry": 1,
        "Dobry": 2,
        "Umiarkowany": 3,
        "Dostateczny": 4,
        "Zły": 5,
        "Bardzo zły": 6,
    }

    _RANK_TO_LABEL = {rank: label for label, rank in _INDEX_RANK.items()}


    def __init__(self, station: dict, sensors: list[dict], aq_index: dict | None = None):
        """
        :param station: dict with station info
        :param sensors: list of dicts with sensor info
        :param aq_index: dict with air quality index
        """
        self._city_id = station.get("city_id")
        self._station_id = station.get("station_id")
        self._station_name = station.get("station_name")
        self._powiat = station.get("powiat")
        self._wojewodztwo = station.get("wojewodztwo")
        self._coords = station.get("coords")

        self._aq_index = aq_index or {}
        self.sensor = {
            s["sensor_id"]: s
            for s in sensors
            if s.get("sensor_id") is not None
        }

    @property
    def overall_station_index(self) -> str:
        """
        Get the main air quality index for the station.
        :return: index name as string
        """
        return self._aq_index.get("overall_index") or "Brak indeksu"


    def to_dict(self) -> dict:
        """
        Convert all station and sensor data to a dictionary.
        :return: dict with all data
        """
        pollutant_indices = self._aq_index.get("pollutants", {})
        individual = {}

        for sensor_id, data in self.sensor.items():
            code = data.get("Kod")
            value = data.get("Value")
            is_stale = data.get("is_stale", True)

            if value is not None and not is_stale:
                sensor_index = pollutant_indices.get(code, "Brak indeksu")
            else:
                sensor_index = "Brak indeksu"

            individual[sensor_id] = {
                "code": code,
                "name": data.get("Name"),
                "value": value,
                "date": data.get("Data"),
                "is_stale": is_stale,
                "index": sensor_index,
            }

        return {
            "city_id": self._city_id,
            "station_id": self._station_id,
            "station_name": self._station_name,
            "powiat": self._powiat,
            "wojewodztwo": self._wojewodztwo,
            "coords": self._coords,
            "overall_index": self.overall_station_index,
            "index_calc_date": self._aq_index.get("calc_date"),
            "sensors": individual,
        }

    @property
    def city_id(self):
        """
        Get city ID.
        """
        return self._city_id

    @property
    def station_id(self):
        """
        Get station ID.
        """
        return self._station_id

    @property
    def station_name(self):
        """
        Get station name.
        """
        return self._station_name

    @property
    def powiat(self):
        """
        Get powiat (district) name.
        """
        return self._powiat

    @property
    def wojewodztwo(self):
        """
        Get voivodeship (region) name.
        """
        return self._wojewodztwo

    @property
    def coords(self) -> dict[str, float] | None:
        """
        Get station coordinates.
        :return: dict with coordinates or None
        """
        return self._coords

    def __str__(self) -> str:
        """
        Return station info as text.
        """
        return (
            f"{self._wojewodztwo} {self._powiat} {self._station_id} ({self._station_name}): {self.overall_station_index}"
        )

    def __repr__(self) -> str:
        """
        Return text representation of the object.
        """
        return self.__str__()