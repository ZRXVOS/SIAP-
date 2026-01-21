"""
GemaScreener Technical Indicators
Implementasi indikator teknikal untuk screening saham
"""

import pandas as pd
import numpy as np


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average"""
    return series.rolling(window=period, min_periods=1).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average"""
    return series.ewm(span=period, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index
    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss
    """
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi_value = 100 - (100 / (1 + rs))
    return rsi_value


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
               k_period: int = 14, d_period: int = 3, smooth_k: int = 3) -> tuple:
    """
    Stochastic Oscillator
    %K = (Current Close - Lowest Low) / (Highest High - Lowest Low) * 100
    %D = SMA of %K
    """
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()

    # Fast %K
    fast_k = 100 * (close - lowest_low) / (highest_high - lowest_low)

    # Slow %K (smoothed)
    slow_k = fast_k.rolling(window=smooth_k).mean()

    # %D
    slow_d = slow_k.rolling(window=d_period).mean()

    return slow_k, slow_d


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Average True Range
    ATR = SMA of True Range
    True Range = max(High-Low, |High-PrevClose|, |Low-PrevClose|)
    """
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return true_range.rolling(window=period).mean()


def cmf(high: pd.Series, low: pd.Series, close: pd.Series,
        volume: pd.Series, period: int = 20) -> pd.Series:
    """
    Chaikin Money Flow
    CMF = Sum(Money Flow Volume, n) / Sum(Volume, n)
    Money Flow Multiplier = ((Close - Low) - (High - Close)) / (High - Low)
    Money Flow Volume = MFM * Volume
    """
    # Avoid division by zero
    hl_diff = high - low
    hl_diff = hl_diff.replace(0, np.nan)

    # Money Flow Multiplier
    mfm = ((close - low) - (high - close)) / hl_diff
    mfm = mfm.fillna(0)

    # Money Flow Volume
    mfv = mfm * volume

    # CMF
    cmf_value = mfv.rolling(window=period).sum() / volume.rolling(window=period).sum()
    return cmf_value


def bollinger_bands(close: pd.Series, period: int = 20, std_dev: int = 2) -> tuple:
    """
    Bollinger Bands
    Middle = SMA(close, period)
    Upper = Middle + (std_dev * STD)
    Lower = Middle - (std_dev * STD)
    """
    middle = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()

    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)

    return upper, middle, lower


def hhv(series: pd.Series, period: int) -> pd.Series:
    """Highest High Value dalam n periode"""
    return series.rolling(window=period).max()


def llv(series: pd.Series, period: int) -> pd.Series:
    """Lowest Low Value dalam n periode"""
    return series.rolling(window=period).min()


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    On Balance Volume
    OBV = cumulative sum of volume based on price direction
    """
    direction = np.where(close > close.shift(1), 1,
                         np.where(close < close.shift(1), -1, 0))
    obv_value = (volume * direction).cumsum()
    return pd.Series(obv_value, index=close.index)


def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Volume Weighted Average Price
    VWAP = Cumulative(Typical Price * Volume) / Cumulative(Volume)
    """
    typical_price = (high + low + close) / 3
    vwap_value = (typical_price * volume).cumsum() / volume.cumsum()
    return vwap_value


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Hitung semua indikator yang diperlukan untuk screening
    Input: DataFrame dengan kolom Open, High, Low, Close, Volume
    Output: DataFrame dengan tambahan kolom indikator
    """
    # Pastikan kolom yang diperlukan ada
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # Calculate Value (Close * Volume)
    df['Value'] = df['Close'] * df['Volume']

    # Moving Averages
    df['SMA5'] = sma(df['Close'], 5)
    df['SMA20'] = sma(df['Close'], 20)
    df['SMA50'] = sma(df['Close'], 50)
    df['SMA200'] = sma(df['Close'], 200)

    # SMA Value
    df['SMA_Value_5'] = sma(df['Value'], 5)

    # RSI
    df['RSI'] = rsi(df['Close'], 14)

    # Stochastic
    df['Stoch_K'], df['Stoch_D'] = stochastic(df['High'], df['Low'], df['Close'])

    # ATR
    df['ATR'] = atr(df['High'], df['Low'], df['Close'], 14)
    df['ATR_Percent'] = (df['ATR'] / df['Close']) * 100

    # CMF
    df['CMF'] = cmf(df['High'], df['Low'], df['Close'], df['Volume'], 20)
    df['CMF_2'] = cmf(df['High'], df['Low'], df['Close'], df['Volume'], 2)

    # Bollinger Bands
    df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = bollinger_bands(df['Close'], 20, 2)

    # HHV dan LLV
    df['HHV_High_20'] = hhv(df['High'], 20)
    df['HHV_Volume_9'] = hhv(df['Volume'], 9)
    df['LLV_Low_9'] = llv(df['Low'], 9)
    df['LLV_Value_5'] = llv(df['Value'], 5)

    # Prev values
    df['Prev_Close'] = df['Close'].shift(1)
    df['Prev_Open'] = df['Open'].shift(1)
    df['Prev_High'] = df['High'].shift(1)
    df['Prev_Low'] = df['Low'].shift(1)
    df['Prev_Volume'] = df['Volume'].shift(1)
    df['Prev_Value'] = df['Value'].shift(1)

    # Prev HHV
    df['Prev_HHV_High_20'] = df['HHV_High_20'].shift(1)
    df['Prev_HHV_Volume_9'] = df['HHV_Volume_9'].shift(1)
    df['Prev_LLV_Low_9'] = df['LLV_Low_9'].shift(1)

    return df


def calculate_intraday_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Hitung indikator untuk data intraday (5 menit)
    """
    if df.empty:
        return df

    df['Close_SMA20'] = sma(df['Close'], 20)
    df['Close_SMA200'] = sma(df['Close'], 200)
    df['HHV_High_20'] = hhv(df['High'], 20)
    df['HHV_Volume_20'] = hhv(df['Volume'], 20)
    df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = bollinger_bands(df['Close'], 20, 2)

    return df
