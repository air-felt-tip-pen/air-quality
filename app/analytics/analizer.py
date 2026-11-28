import os
import pandas as pd


class CreateCSV:
    def __init__(self, path: str = "data/"):
        self.path = path
        self.data = pd.DataFrame()

    def _rec_to_dict(self, data):
        if isinstance(data, (list, tuple)):
            return [self._rec_to_dict(item) for item in data]
        if isinstance(data, dict):
            return {k: self._rec_to_dict(v) for k, v in data.items()}
        if hasattr(data, "to_dict"):
            return self._rec_to_dict(data.to_dict())
        return data

    def _load(self, data: dict):
        pure_data = self._rec_to_dict(data)

        stations = []
        for region_stations in pure_data.values():
            for st in region_stations:
                stations.append(st)

        rows = []
        for st in stations:
            raw_sensors = st.get("sensors", {})
            sensors = {s["code"]: s["value"] for s in raw_sensors.values()}

            rows.append({
                "wojewodztwo": st.get("wojewodztwo"),
                "powiat": st.get("powiat"),
                "station_id": st.get("station_id"),
                "sensors_count": st.get("sensors_count", len(raw_sensors)),
                "overall_index": st.get("overall_index"),
                "index_rank": st.get("index_rank"),
                "PM10": sensors.get("PM10"),
                "PM2.5": sensors.get("PM2.5"),
                "O3": sensors.get("O3"),
                "NO2": sensors.get("NO2"),
            })

        self.data = pd.DataFrame(rows)
        self.data["index_rank"] = self.data["index_rank"].astype("Int64")

    def info(self):
        print(self.data.head())
        print(self.data.info())

    def create_csv(self, data: dict) -> None:
        self._load(data)
        os.makedirs(self.path, exist_ok=True)
        self.data.to_csv(os.path.join(self.path, "data.csv"), index=False, encoding="utf-8-sig")



class AirQualityAnalyzer:
    def __init__(self, path: str = "data/"):
        self.path = path
        self.csv = CreateCSV(path)

    def analyze(self, data: dict):
        self.csv.create_csv(data)
        self.data = self.csv.data