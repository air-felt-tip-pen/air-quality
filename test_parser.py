from parser import GiosParser


if __name__ == "__main__":
    gios = GiosParser()
    print("⏳ Завантаження даних з API GIOŚ...")

    gios.fetch()

    print("\n" + "=" * 75)
    print("              ЗВІТ ПРО ЯКІСТЬ ПОВІТРЯ (GIOŚ AIR QUALITY REPORT)")
    print("=" * 75)

    INDEX_EMOJI = {
        "Bardzo dobry": "🟢",
        "Dobry": "🟡",
        "Umiarkowany": "🟠",
        "Dostateczny": "🟧",
        "Zły": "🔴",
        "Bardzo zły": "🟣",
        "Brak indeksu": "⚪"
    }

    for station_data in gios.show():
        overall_index = station_data.get_overall_station_index()
        overall_emoji = INDEX_EMOJI.get(overall_index, "⚪")
        full_status = station_data.get_full_status()

        print(f"\n📍 СТАНЦІЯ ID: {station_data.station_id:<4} | Повіт: {station_data.powiat} | Координати: {station_data.coords}")
        print(f"📊 Загальний індекс повітря: {overall_emoji} [{overall_index.upper()}]")
        print("-" * 75)

        active_sensors = {code: info for code, info in full_status["sensors"].items() if info["value"] is not None}
        inactive_sensors = [code for code, info in full_status["sensors"].items() if info["value"] is None]

        if active_sensors:
            print("  🟢 Активні показники:")
            for code, info in active_sensors.items():
                val = info['value']
                idx = info['index']
                name = info['name'] or "Невідомо"
                emoji = INDEX_EMOJI.get(idx, "⚪")
                print(f"     • {code:<8} ({name:<30}): {val:>6.1f} µg/m³  --> {emoji} [{idx}]")
        else:
            print("  ⚠️ Немає активних автоматичних вимірювань за поточну годину")

        if inactive_sensors:
            missing_list = ", ".join(inactive_sensors)
            print(f"\n  ⚪ Відсутні/Неактивні датчики ({len(inactive_sensors)}): {missing_list}")

        print("-" * 75)