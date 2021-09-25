from pathlib import Path
import pandas as pd
from scipy.interpolate import interp1d
from functools import lru_cache


def validate_data_dir(data_dir):
    data_dir = Path(data_dir).resolve()

    assert (data_dir / "CH 2020-2021.csv").exists()
    assert (data_dir / "metervalues_pseudonymized_1_neu.csv").exists()
    assert (data_dir / "metervalues_pseudonymized_2_neu.csv").exists()

    return data_dir


def load_meter_data(data_dir):
    data_dir = validate_data_dir(data_dir)

    meter_1 = pd.read_csv(
        data_dir / "metervalues_pseudonymized_1_neu.csv", delimiter=";"
    )

    # Clean extra row of headers
    meter_1 = meter_1[meter_1["id"] != "id"]

    # Convert to correct datatypes
    meter_1["id"] = pd.to_numeric(meter_1["id"])
    meter_1["timestamp"] = pd.to_datetime(meter_1["timestamp"])
    meter_1["Chargepoint"] = meter_1["Chargepoint"].apply(int)
    meter_1["metervalue"] = pd.to_numeric(meter_1["metervalue"])
    meter_1["increment"] = pd.to_numeric(meter_1["increment"])

    meter_2 = pd.read_csv(
        data_dir / "metervalues_pseudonymized_2_neu.csv", delimiter=";", header=0
    )

    # Convert to correct datatypes
    meter_2["id"] = pd.to_numeric(meter_2["id"])
    meter_2["timestamp"] = pd.to_datetime(meter_2["timestamp"])
    mask = meter_2["Chargepoint"].isnull()
    meter_2["Chargepoint"][mask] = 42
    meter_2["Chargepoint"] = meter_2["Chargepoint"].apply(int)
    meter_2["metervalue"] = pd.to_numeric(meter_2["metervalue"])
    meter_2["increment"] = pd.to_numeric(meter_2["increment"])

    meter = pd.concat([meter_1, meter_2])
    meter_1 = meter_2 = None

    # replace NaN Chargpoints with unique number based on UUID of the connector
    nan_mask = meter["Chargepoint"].isna()
    nan_cp_connectors = meter[nan_mask]["connector"].unique()
    for i, connector in enumerate(nan_cp_connectors):
        meter[nan_mask].loc[
            meter[nan_mask]["connector"] == connector, ["Chargepoint"]
        ] = (
            i + 10000
        )  # Arbitrary offset

    return meter


def load_co2_data(data_dir):
    data_dir = validate_data_dir(data_dir)

    co2 = pd.read_csv(data_dir / "CH 2020-2021.csv")

    UNNECESSARY = [
        "created_at",
        "updated_at",
        "timestamp",
        "zone_name",
        "carbon_intensity_discharge_avg",
        "carbon_origin_percent_nuclear_avg",
        "carbon_origin_percent_geothermal_avg",
        "carbon_origin_percent_biomass_avg",
        "carbon_origin_percent_coal_avg",
        "carbon_origin_percent_wind_avg",
        "carbon_origin_percent_solar_avg",
        "carbon_origin_percent_hydro_avg",
        "carbon_origin_percent_gas_avg",
        "carbon_origin_percent_oil_avg",
        "carbon_origin_percent_unknown_avg",
        "carbon_origin_percent_battery_discharge_avg",
        "carbon_origin_percent_hydro_discharge_avg",
        "power_net_discharge_battery_avg",
        "power_net_discharge_hydro_avg",
        "power_net_import_AT_avg",
        "carbon_intensity_exchange_AT_avg",
        "power_net_import_DE_avg",
        "carbon_intensity_exchange_DE_avg",
        "power_net_import_FR_avg",
        "carbon_intensity_exchange_FR_avg",
        "power_net_import_IT-NO_avg",
        "carbon_intensity_exchange_IT-NO_avg",
        "latest_forecasted_wind_x_avg",
        "latest_forecasted_wind_y_avg",
        "latest_forecasted_solar_avg",
        "latest_forecasted_temperature_avg",
        "latest_forecasted_dewpoint_avg",
        "latest_forecasted_precipitation_avg",
        "latest_forecasted_price_avg",
        "latest_forecasted_production_avg",
        "latest_forecasted_consumption_avg",
        "latest_forecasted_power_net_import_AT_avg",
        "latest_forecasted_power_net_import_DE_avg",
        "latest_forecasted_power_net_import_FR_avg",
        "latest_forecasted_power_net_import_IT-NO_avg",
        "latest_forecasted_production_solar_avg",
        "latest_forecasted_production_wind_avg",
        "power_origin_percent_fossil_avg",
        "power_origin_percent_renewable_avg",
        "power_production_percent_fossil_avg",
        "power_production_percent_renewable_avg",
        "power_production_nuclear_avg",
        "power_production_geothermal_avg",
        "power_production_biomass_avg",
        "power_production_coal_avg",
        "power_production_wind_avg",
        "power_production_solar_avg",
        "power_production_hydro_avg",
        "power_production_gas_avg",
        "power_production_oil_avg",
        "power_production_unknown_avg",
        "carbon_rate_avg",
        "total_storage_avg",
        "total_discharge_avg",
        "total_import_avg",
        "total_export_avg",
        "production_sources",
    ]

    co2.drop(UNNECESSARY, axis=1, inplace=True)

    # Convert to correct datatype
    co2["datetime"] = pd.to_datetime(co2["datetime"])

    mapping = {
        "carbon_intensity_avg": "co2_intensity",  # g / kWh
        "carbon_intensity_production_avg": "co2_production",
        "carbon_intensity_import_avg": "co2_import",
        "power_consumption_nuclear_avg": "nuclear",
        "power_consumption_geothermal_avg": "geothermal",
        "power_consumption_biomass_avg": "biomass",
        "power_consumption_coal_avg": "coal",
        "power_consumption_wind_avg": "wind",
        "power_consumption_solar_avg": "solar",
        "power_consumption_hydro_avg": "hydro",
        "power_consumption_gas_avg": "gas",
        "power_consumption_oil_avg": "oil",
        "power_consumption_unknown_avg": "unknown",
        "power_consumption_battery_discharge_avg": "battery",
        "power_consumption_hydro_discharge_avg": "hydro",
        "total_consumption_avg": "consumption",
        "total_production_avg": "production",
    }

    co2.rename(mapping, axis=1, inplace=True)
    return co2


def load_annotated_meter_data(data_dir):
    data_dir = validate_data_dir(data_dir)

    meter = load_meter_data(data_dir)
    co2 = load_co2_data(data_dir)

    epoch = pd.to_datetime(0, utc=True)
    neutral_epoch = pd.to_datetime(0)

    def to_unix_timestamp(x):
        return (x - epoch).total_seconds()

    def to_unix_timestamp_neutral(x):
        return (x - neutral_epoch).total_seconds()

    interp_dict = {}

    for x in range(int(len(co2) / 24)):
        if x == 0:
            start, end = x * 24, (x + 1) * 24 + 6
        elif x == 546:
            start, end = x * 24 - 6, (x + 1) * 24
        else:
            start, end = x * 24 - 6, (x + 1) * 24 + 6
        xs = co2["datetime"][start:end].apply(to_unix_timestamp)
        ys = co2["co2_intensity"][start:end]
        dt = co2["datetime"][x * 24]
        interp_dict[(dt.year, dt.month, dt.day)] = interp1d(xs, ys, kind="cubic")

    @lru_cache(maxsize=512)
    def get_co2_for_datetime(dt, interp_dict=interp_dict):
        try:
            func = interp_dict[(dt.year, dt.month, dt.day)]
            as_ts = to_unix_timestamp_neutral(dt)
            end_value = float(func(as_ts))
            try:
                start_value = float(func(as_ts - (15 * 60)))  # Fifteen minutes earlier
            except ValueError:
                start_value = end_value
            return (start_value + end_value) / 2
        except (KeyError, ValueError):
            return 0

    meter["co2_intensity"] = meter["timestamp"].apply(get_co2_for_datetime)
    meter["co2_total"] = meter["co2_intensity"] * (
        meter["increment"] / 1000 / 1000 / 4  # Convert g CO2 to kg  # Convert Wh to kWh
    )  # Convert 15 minutes to hour

    meter = meter.astype({"Chargepoint": str, "connector": str, "charge_log_id": str})
    meter["unique_charge_point"] = meter["Chargepoint"] + "|" + meter["connector"]

    return meter
