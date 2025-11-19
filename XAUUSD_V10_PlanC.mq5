//+------------------------------------------------------------------+
//|                                            XAUUSD_V10_PlanC.mq5 |
//|                                 Converted from TradingView V10  |
//|                             Target: PF 4.0 | Multi-Filter System|
//+------------------------------------------------------------------+
#property copyright "V10 Plan C - High PF Strategy"
#property link      "https://github.com/yourrepo"
#property version   "10.00"
#property description "XAUUSD Supertrend + Daily Filter + Volume + Confirmation"
#property strict

//--- Input Parameters
input group "===== CORE SETTINGS ====="
input int InpATRPeriod = 12;                    // ATR Period
input double InpATRMultiplier = 4.0;            // ATR Multiplier (V10: 4.0)

input group "===== FILTERS ====="
input bool InpUseDailyFilter = true;            // Enable Daily Trend Filter
input bool InpUseVolumeFilter = true;           // Enable Volume Filter
input double InpVolumeMultiplier = 1.0;         // Volume Multiplier
input bool InpUseConfirmation = true;           // Enable Confirmation Candle

input group "===== DAILY FILTER ====="
input int InpDailyATRPeriod = 12;              // Daily ATR Period
input double InpDailyATRMultiplier = 3.0;      // Daily ATR Multiplier

input group "===== RISK MANAGEMENT ====="
input double InpStopLossPercent = 4.0;         // Stop Loss %
input bool InpUseTrailingStop = true;          // Enable Trailing Stop
input double InpTrailActivation = 4.5;         // Trail Activation %
input double InpTrailOffset = 2.5;             // Trail Offset %

input group "===== DAILY LIMITS ====="
input bool InpEnableDailyTarget = false;       // Enable Daily Target
input double InpDailyTarget = 3.0;             // Daily Target %
input bool InpEnableDailyStop = false;         // Enable Daily Stop Loss
input double InpDailyStopLoss = 8.0;           // Daily Stop Loss %

input group "===== POSITION SETTINGS ====="
input double InpLotSize = 0.02;                // Lot Size (fixed)
input bool InpAllowLong = true;                // Allow Long
input bool InpAllowShort = false;              // Allow Short
input int InpMagicNumber = 100010;             // Magic Number

input group "===== DISPLAY ====="
input bool InpShowInfo = true;                 // Show Info Panel
input color InpInfoColor = clrWhite;           // Info Text Color

//--- Global Variables
int handleATR, handleDailyATR;
int handleVolume;
double atrBuffer[], dailyATRBuffer[];
double volumeBuffer[], volumeMABuffer[];
datetime lastBarTime = 0;
bool pendingLong = false;
bool pendingShort = false;
double entryPrice = 0;
double stopLossPrice = 0;
double trailStopPrice = 0;
double dayStartBalance = 0;
int currentDay = 0;

//--- Supertrend buffers
double supertrendBuffer[];
int supertrendDirection[];
double dailySupertrendBuffer[];
int dailySupertrendDirection[];

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    //--- Create ATR indicator handle
    handleATR = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
    if(handleATR == INVALID_HANDLE)
    {
        Print("Error creating ATR indicator");
        return(INIT_FAILED);
    }

    //--- Create Daily ATR handle
    handleDailyATR = iATR(_Symbol, PERIOD_D1, InpDailyATRPeriod);
    if(handleDailyATR == INVALID_HANDLE)
    {
        Print("Error creating Daily ATR indicator");
        return(INIT_FAILED);
    }

    //--- Initialize day tracking
    MqlDateTime dt;
    TimeCurrent(dt);
    currentDay = dt.day;
    dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);

    //--- Set array as series
    ArraySetAsSeries(atrBuffer, true);
    ArraySetAsSeries(dailyATRBuffer, true);
    ArraySetAsSeries(volumeBuffer, true);
    ArraySetAsSeries(volumeMABuffer, true);
    ArraySetAsSeries(supertrendBuffer, true);
    ArraySetAsSeries(dailySupertrendBuffer, true);

    Print("V10 Plan C EA initialized successfully");
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    //--- Release indicator handles
    if(handleATR != INVALID_HANDLE)
        IndicatorRelease(handleATR);
    if(handleDailyATR != INVALID_HANDLE)
        IndicatorRelease(handleDailyATR);

    Comment("");
    Print("V10 Plan C EA deinitialized");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    //--- Check for new bar
    datetime currentBarTime = iTime(_Symbol, PERIOD_CURRENT, 0);
    bool isNewBar = (currentBarTime != lastBarTime);

    if(!isNewBar)
    {
        //--- Update trailing stop even on non-new bars
        ManageTrailingStop();
        return;
    }

    lastBarTime = currentBarTime;

    //--- Check daily reset
    CheckDailyReset();

    //--- Update indicators
    if(!UpdateIndicators())
        return;

    //--- Check daily limits
    if(CheckDailyLimits())
    {
        CloseAllPositions("Daily Limit Reached");
        return;
    }

    //--- Calculate Supertrend
    CalculateSupertrend();
    CalculateDailySupertrend();

    //--- Check for trading signals
    CheckTradingSignals();

    //--- Manage existing positions
    ManagePositions();

    //--- Display info panel
    if(InpShowInfo)
        DisplayInfoPanel();
}

//+------------------------------------------------------------------+
//| Update indicator buffers                                         |
//+------------------------------------------------------------------+
bool UpdateIndicators()
{
    //--- Copy ATR values
    if(CopyBuffer(handleATR, 0, 0, 3, atrBuffer) <= 0)
    {
        Print("Error copying ATR buffer");
        return false;
    }

    //--- Copy Daily ATR values
    if(CopyBuffer(handleDailyATR, 0, 0, 3, dailyATRBuffer) <= 0)
    {
        Print("Error copying Daily ATR buffer");
        return false;
    }

    //--- Get volume data
    if(InpUseVolumeFilter)
    {
        ArrayResize(volumeBuffer, 21);
        ArrayResize(volumeMABuffer, 21);

        for(int i = 0; i < 21; i++)
        {
            volumeBuffer[i] = (double)iVolume(_Symbol, PERIOD_CURRENT, i);
        }

        //--- Calculate volume MA
        for(int i = 0; i < 1; i++)
        {
            double sum = 0;
            for(int j = 0; j < 20; j++)
            {
                sum += volumeBuffer[i + j];
            }
            volumeMABuffer[i] = sum / 20.0;
        }
    }

    return true;
}

//+------------------------------------------------------------------+
//| Calculate Supertrend                                             |
//+------------------------------------------------------------------+
void CalculateSupertrend()
{
    ArrayResize(supertrendBuffer, 3);
    ArrayResize(supertrendDirection, 3);

    for(int i = 0; i < 3; i++)
    {
        double hl2 = (iHigh(_Symbol, PERIOD_CURRENT, i) + iLow(_Symbol, PERIOD_CURRENT, i)) / 2.0;
        double atr = atrBuffer[i];

        double upperBand = hl2 + (InpATRMultiplier * atr);
        double lowerBand = hl2 - (InpATRMultiplier * atr);

        double close = iClose(_Symbol, PERIOD_CURRENT, i);

        //--- Determine direction
        if(i == 0)
        {
            if(close > supertrendBuffer[1])
                supertrendDirection[i] = 1; // Bullish
            else if(close < supertrendBuffer[1])
                supertrendDirection[i] = -1; // Bearish
            else
                supertrendDirection[i] = supertrendDirection[1];
        }

        //--- Set supertrend value
        if(supertrendDirection[i] == 1)
            supertrendBuffer[i] = lowerBand;
        else
            supertrendBuffer[i] = upperBand;
    }
}

//+------------------------------------------------------------------+
//| Calculate Daily Supertrend                                       |
//+------------------------------------------------------------------+
void CalculateDailySupertrend()
{
    ArrayResize(dailySupertrendBuffer, 3);
    ArrayResize(dailySupertrendDirection, 3);

    for(int i = 0; i < 3; i++)
    {
        double hl2 = (iHigh(_Symbol, PERIOD_D1, i) + iLow(_Symbol, PERIOD_D1, i)) / 2.0;
        double atr = dailyATRBuffer[i];

        double upperBand = hl2 + (InpDailyATRMultiplier * atr);
        double lowerBand = hl2 - (InpDailyATRMultiplier * atr);

        double close = iClose(_Symbol, PERIOD_D1, i);

        //--- Determine direction
        if(i == 0)
        {
            if(close > dailySupertrendBuffer[1])
                dailySupertrendDirection[i] = 1; // Bullish
            else if(close < dailySupertrendBuffer[1])
                dailySupertrendDirection[i] = -1; // Bearish
            else
                dailySupertrendDirection[i] = dailySupertrendDirection[1];
        }

        //--- Set supertrend value
        if(dailySupertrendDirection[i] == 1)
            dailySupertrendBuffer[i] = lowerBand;
        else
            dailySupertrendBuffer[i] = upperBand;
    }
}

//+------------------------------------------------------------------+
//| Check trading signals                                            |
//+------------------------------------------------------------------+
void CheckTradingSignals()
{
    //--- No new positions if already in trade
    if(PositionSelect(_Symbol))
        return;

    //--- Check supertrend flip
    bool bullishFlip = (supertrendDirection[1] == -1 && supertrendDirection[0] == 1);
    bool bearishFlip = (supertrendDirection[1] == 1 && supertrendDirection[0] == -1);

    //--- Daily trend check
    bool dailyBullish = (dailySupertrendDirection[0] == 1);
    bool dailyBearish = (dailySupertrendDirection[0] == -1);

    bool dailyTrendOK = !InpUseDailyFilter ||
                        (InpAllowLong && dailyBullish) ||
                        (InpAllowShort && dailyBearish);

    //--- Volume check
    bool highVolume = true;
    if(InpUseVolumeFilter)
    {
        highVolume = (volumeBuffer[0] > volumeMABuffer[0] * InpVolumeMultiplier);
    }

    bool volumeOK = !InpUseVolumeFilter || highVolume;

    //--- Confirmation logic
    if(InpUseConfirmation)
    {
        if(bullishFlip && dailyTrendOK && volumeOK)
        {
            pendingLong = true;
            pendingShort = false;
        }
        else if(bearishFlip && dailyTrendOK && volumeOK)
        {
            pendingShort = true;
            pendingLong = false;
        }

        //--- Cancel pending if price goes wrong way
        double close = iClose(_Symbol, PERIOD_CURRENT, 0);
        if(pendingLong && close < supertrendBuffer[0])
            pendingLong = false;
        if(pendingShort && close > supertrendBuffer[0])
            pendingShort = false;
    }
    else
    {
        pendingLong = bullishFlip && dailyTrendOK && volumeOK;
        pendingShort = bearishFlip && dailyTrendOK && volumeOK;
    }

    //--- Confirmed signals
    double close = iClose(_Symbol, PERIOD_CURRENT, 0);
    bool confirmedLong = pendingLong && close > supertrendBuffer[0] && dailyTrendOK && volumeOK;
    bool confirmedShort = pendingShort && close < supertrendBuffer[0] && dailyTrendOK && volumeOK;

    //--- Execute trades
    if(confirmedLong && InpAllowLong)
    {
        OpenPosition(ORDER_TYPE_BUY);
        pendingLong = false;
    }

    if(confirmedShort && InpAllowShort)
    {
        OpenPosition(ORDER_TYPE_SELL);
        pendingShort = false;
    }
}

//+------------------------------------------------------------------+
//| Open position                                                     |
//+------------------------------------------------------------------+
void OpenPosition(ENUM_ORDER_TYPE orderType)
{
    MqlTradeRequest request;
    MqlTradeResult result;
    ZeroMemory(request);
    ZeroMemory(result);

    double price = (orderType == ORDER_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);

    //--- Calculate stop loss
    double slDistance = price * InpStopLossPercent / 100.0;
    double sl = (orderType == ORDER_TYPE_BUY) ? price - slDistance : price + slDistance;

    //--- Normalize prices
    sl = NormalizeDouble(sl, _Digits);

    //--- Fill request
    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = InpLotSize;
    request.type = orderType;
    request.price = price;
    request.sl = sl;
    request.tp = 0; // No TP, using trailing stop
    request.deviation = 10;
    request.magic = InpMagicNumber;
    request.comment = "V10 Entry";

    //--- Send order
    if(OrderSend(request, result))
    {
        if(result.retcode == TRADE_RETCODE_DONE)
        {
            Print("Position opened: ", (orderType == ORDER_TYPE_BUY ? "BUY" : "SELL"), " at ", price);
            entryPrice = price;
            stopLossPrice = sl;
            trailStopPrice = 0;
        }
        else
        {
            Print("Order failed: ", result.retcode, " - ", result.comment);
        }
    }
    else
    {
        Print("OrderSend error: ", GetLastError());
    }
}

//+------------------------------------------------------------------+
//| Manage existing positions                                        |
//+------------------------------------------------------------------+
void ManagePositions()
{
    if(!PositionSelect(_Symbol))
        return;

    //--- Check for opposite supertrend flip
    bool bullishFlip = (supertrendDirection[1] == -1 && supertrendDirection[0] == 1);
    bool bearishFlip = (supertrendDirection[1] == 1 && supertrendDirection[0] == -1);

    long posType = PositionGetInteger(POSITION_TYPE);

    if(posType == POSITION_TYPE_BUY && bearishFlip)
    {
        CloseAllPositions("Supertrend Reverse");
        pendingLong = false;
    }
    else if(posType == POSITION_TYPE_SELL && bullishFlip)
    {
        CloseAllPositions("Supertrend Reverse");
        pendingShort = false;
    }
}

//+------------------------------------------------------------------+
//| Manage trailing stop                                             |
//+------------------------------------------------------------------+
void ManageTrailingStop()
{
    if(!InpUseTrailingStop)
        return;

    if(!PositionSelect(_Symbol))
        return;

    long posType = PositionGetInteger(POSITION_TYPE);
    double posOpenPrice = PositionGetDouble(POSITION_PRICE_OPEN);
    double currentSL = PositionGetDouble(POSITION_SL);

    double currentPrice = (posType == POSITION_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);

    double profitPercent = 0;
    if(posType == POSITION_TYPE_BUY)
        profitPercent = ((currentPrice - posOpenPrice) / posOpenPrice) * 100.0;
    else
        profitPercent = ((posOpenPrice - currentPrice) / posOpenPrice) * 100.0;

    //--- Check if profit reached activation level
    if(profitPercent >= InpTrailActivation)
    {
        double newSL = 0;

        if(posType == POSITION_TYPE_BUY)
        {
            newSL = currentPrice * (1 - InpTrailOffset / 100.0);
            newSL = NormalizeDouble(newSL, _Digits);

            //--- Only move SL up
            if(newSL > currentSL)
            {
                ModifyPosition(newSL, 0);
            }
        }
        else // SELL
        {
            newSL = currentPrice * (1 + InpTrailOffset / 100.0);
            newSL = NormalizeDouble(newSL, _Digits);

            //--- Only move SL down
            if(newSL < currentSL || currentSL == 0)
            {
                ModifyPosition(newSL, 0);
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Modify position SL/TP                                            |
//+------------------------------------------------------------------+
void ModifyPosition(double sl, double tp)
{
    MqlTradeRequest request;
    MqlTradeResult result;
    ZeroMemory(request);
    ZeroMemory(result);

    request.action = TRADE_ACTION_SLTP;
    request.symbol = _Symbol;
    request.sl = sl;
    request.tp = tp;
    request.magic = InpMagicNumber;

    if(OrderSend(request, result))
    {
        if(result.retcode == TRADE_RETCODE_DONE)
        {
            Print("Position modified: SL=", sl, " TP=", tp);
        }
    }
}

//+------------------------------------------------------------------+
//| Close all positions                                              |
//+------------------------------------------------------------------+
void CloseAllPositions(string comment)
{
    MqlTradeRequest request;
    MqlTradeResult result;

    if(PositionSelect(_Symbol))
    {
        ZeroMemory(request);
        ZeroMemory(result);

        long posType = PositionGetInteger(POSITION_TYPE);
        double volume = PositionGetDouble(POSITION_VOLUME);

        request.action = TRADE_ACTION_DEAL;
        request.symbol = _Symbol;
        request.volume = volume;
        request.type = (posType == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
        request.price = (posType == POSITION_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
        request.deviation = 10;
        request.magic = InpMagicNumber;
        request.comment = comment;

        OrderSend(request, result);

        //--- Reset variables
        entryPrice = 0;
        stopLossPrice = 0;
        trailStopPrice = 0;
    }
}

//+------------------------------------------------------------------+
//| Check daily reset                                                |
//+------------------------------------------------------------------+
void CheckDailyReset()
{
    MqlDateTime dt;
    TimeCurrent(dt);

    if(dt.day != currentDay)
    {
        currentDay = dt.day;
        dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
    }
}

//+------------------------------------------------------------------+
//| Check daily limits                                               |
//+------------------------------------------------------------------+
bool CheckDailyLimits()
{
    double currentBalance = AccountInfoDouble(ACCOUNT_BALANCE);
    double dailyPnL = currentBalance - dayStartBalance;
    double dailyPnLPercent = (dailyPnL / dayStartBalance) * 100.0;

    if(InpEnableDailyTarget && dailyPnLPercent >= InpDailyTarget)
    {
        Print("Daily target reached: ", dailyPnLPercent, "%");
        return true;
    }

    if(InpEnableDailyStop && dailyPnLPercent <= -InpDailyStopLoss)
    {
        Print("Daily stop loss hit: ", dailyPnLPercent, "%");
        return true;
    }

    return false;
}

//+------------------------------------------------------------------+
//| Display info panel                                               |
//+------------------------------------------------------------------+
void DisplayInfoPanel()
{
    string info = "\n===== V10 PLAN C =====\n";

    //--- Supertrend status
    info += "15m Trend: " + (supertrendDirection[0] == 1 ? "BULL" : "BEAR") + "\n";
    info += "Daily Trend: " + (dailySupertrendDirection[0] == 1 ? "BULL" : "BEAR") + "\n";

    //--- Volume status
    if(InpUseVolumeFilter)
    {
        bool highVol = (volumeBuffer[0] > volumeMABuffer[0] * InpVolumeMultiplier);
        info += "Volume: " + (highVol ? "HIGH" : "LOW") + "\n";
    }

    //--- Filters status
    info += "Filters: " + (InpUseDailyFilter ? "1" : "0") + "/" +
                          (InpUseVolumeFilter ? "1" : "0") + "/" +
                          (InpUseConfirmation ? "1" : "0") + "\n";

    //--- Position status
    if(PositionSelect(_Symbol))
    {
        long posType = PositionGetInteger(POSITION_TYPE);
        double posProfit = PositionGetDouble(POSITION_PROFIT);
        info += "Position: " + (posType == POSITION_TYPE_BUY ? "LONG" : "SHORT") + "\n";
        info += "P/L: " + DoubleToString(posProfit, 2) + " USD\n";
    }
    else
    {
        info += "Position: NONE\n";
    }

    //--- Daily P/L
    double currentBalance = AccountInfoDouble(ACCOUNT_BALANCE);
    double dailyPnL = currentBalance - dayStartBalance;
    double dailyPnLPercent = (dailyPnL / dayStartBalance) * 100.0;
    info += "Daily P/L: " + DoubleToString(dailyPnLPercent, 2) + "%\n";

    Comment(info);
}
//+------------------------------------------------------------------+
