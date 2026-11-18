class DataNormalizer:


    def clean(self, data):

        clean_data = {}

        for region, stations in data.items():

            clean_stations = []
            clean_data[region] = clean_stations


            for station in stations:
                clean_sensors = {}
                sensors = station.sensor

                station_data = station.to_dict()
                clean_stations.append(station_data)

                
                for sensor_id, sensor in sensors.items():

                    if sensor["Value"] is None or sensor["is_stale"]:
                        continue

                    clean_sensors[sensor_id] = sensor
                station_data["sensors"] = clean_sensors


        return clean_data