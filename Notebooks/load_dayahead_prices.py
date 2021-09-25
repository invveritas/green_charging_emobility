import pandas as pd
import numpy as np
import datetime
import pytz


def load_dayahead_prices(filepath, in_utc=True, local_time=False, shift_time="start"):
    """
    Load entsoe day-ahead price data and standardize to format with correct datetime index and 15min/60min resolution

    Parameters
    ----------
    filepath : str
        filepath to file of entso-e data (is in CET).
    local_time : bool, optional
        if True, the data is converted to local time, by default False
    shift_time : str, optional
        Which part of the time range provided by ENTSO-E to take as timestamp, one of ["start", "center", "end"], by default True

    Returns
    -------
    pandas DataFrame
        Dataframe of the standardized ENTSO-E data.
    """

    df = pd.read_csv(filepath)
    df = df.replace('n/e', np.nan)
    df = df.replace('', np.nan)
    df = df.replace('-', np.nan)
    # (!) convert eu time format to us time format:
    df['datetime'] = df["MTU (CET)"].apply(
        lambda x: datetime.datetime.strptime(x[:16].replace('.', '/'), '%d/%m/%Y %H:%M').strftime(
            '%Y-%m-%d %H:%M:%S'))  # exctract starting time from time period strings
    df.drop(["MTU (CET)"], axis=1, inplace=True)

    df['datetime'] = pd.to_datetime(df['datetime'])
    if shift_time == "center":
        freq = df['datetime'][1] - df['datetime'][0]  # extract frequency (60min for CH, IT, FR ; 15min for AT, DE)
        df['datetime'] = pd.to_datetime(
            df['datetime']) + freq / 2  # Shift timestamp so that it lies in the center of the period

    elif shift_time == "end":
        freq = df['datetime'][1] - df['datetime'][0]  # extract frequency (60min for CH, IT, FR ; 15min for AT, DE)
        df['datetime'] = pd.to_datetime(df['datetime']) + freq

    # df.set_index('datetime', inplace=True)
    df["Day-ahead Price [EUR/MWh]"] = pd.to_numeric(df["Day-ahead Price [EUR/MWh]"], downcast="float")

    if in_utc is True:
        # convert to local time:
        df['datetime'] = df['datetime'].dt.tz_localize('Europe/Zurich', ambiguous="infer", nonexistent="NaT").dt.tz_convert('UTC')

    return df
