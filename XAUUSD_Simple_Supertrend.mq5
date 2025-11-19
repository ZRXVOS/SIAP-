//+------------------------------------------------------------------+
//|                                      XAUUSD_Simple_Supertrend.mq5|
//|                                              Simplified V8 Logic |
//|                                   Pure Supertrend - NO FILTERS  |
//+------------------------------------------------------------------+
#property copyright "Simple Supertrend EA - Based on V8"
#property version   "8.00"
#property description "Pure Supertrend - Guaranteed to Trade"
#property strict

//--- Input Parameters
input group "===== CORE SETTINGS ====="
input int InpATRPeriod = 12;                    // ATR Period
input double InpATRMultiplier = 3.0;            // ATR Multiplier (V8: 3.0)

input group "===== RISK MANAGEMENT ====="
input double InpStopLossPercent = 4.0;         // Stop Loss %
input bool InpUseTrailingStop = true;          // Enable Trailing Stop
input double InpTrailActivation = 4.5;         // Trail Activation %
input double InpTrailOffset = 2.5;             // Trail Offset %

input group "===== POSITION SETTINGS ====="
input double InpLotSize = 0.02;                // Lot Size
input bool InpAllowLong = true;                // Allow Long
input bool InpAllowShort = false;              // Allow Short
input int InpMagicNumber = 80008;              // Magic Number

input group "===== DEBUG ====="
input bool InpPrintSignals = true;             // Print Signals to Log

//--- Global Variables
int handleATR;
double atrBuffer[];
datetime lastBarTime = 0;
int lastDirection = 0;
double lastSupertrend = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    //--- Create ATR indicator
    handleATR = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
    if(handleATR == INVALID_HANDLE)
    {
        Print("ERROR: Failed to create ATR indicator");
        return(INIT_FAILED);
    }

    //--- Set array as series
    ArraySetAsSeries(atrBuffer, true);

    Print("==============================================");
    Print("Simple Supertrend EA Initialized Successfully");
    Print("Symbol: ", _Symbol);
    Print("Timeframe: ", EnumToString(PERIOD_CURRENT));
    Print("ATR Period: ", InpATRPeriod);
    Print("ATR Multiplier: ", InpATRMultiplier);
    Print("Lot Size: ", InpLotSize);
    Print("==============================================");

    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    if(handleATR != INVALID_HANDLE)
        IndicatorRelease(handleATR);
    Comment("");
    Print("Simple Supertrend EA Stopped");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    //--- Check for new bar
    datetime currentBarTime = iTime(_Symbol, PERIOD_CURRENT, 0);
    if(currentBarTime == lastBarTime)
    {
        ManageTrailingStop();
        return;
    }

    lastBarTime = currentBarTime;

    //--- Update indicators
    if(CopyBuffer(handleATR, 0, 0, 50, atrBuffer) <= 0)
    {
        if(InpPrintSignals)
            Print("ERROR: Failed to copy ATR buffer");
        return;
    }

    //--- Calculate Supertrend
    CalculateSupertrend();

    //--- Check for signals
    CheckSignals();

    //--- Manage positions
    ManagePositions();

    //--- Update display
    UpdateDisplay();
}

//+------------------------------------------------------------------+
//| Calculate Supertrend                                             |
//+------------------------------------------------------------------+
void CalculateSupertrend()
{
    double high1 = iHigh(_Symbol, PERIOD_CURRENT, 1);
    double low1 = iLow(_Symbol, PERIOD_CURRENT, 1);
    double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
    double hl2 = (high1 + low1) / 2.0;

    double upperBand = hl2 + (InpATRMultiplier * atrBuffer[1]);
    double lowerBand = hl2 - (InpATRMultiplier * atrBuffer[1]);

    //--- Determine Supertrend direction and value
    int currentDirection = 0;
    double currentSupertrend = 0;

    if(lastDirection == 0)  // First calculation
    {
        if(close1 > upperBand)
        {
            currentDirection = 1;  // Bullish
            currentSupertrend = lowerBand;
        }
        else
        {
            currentDirection = -1; // Bearish
            currentSupertrend = upperBand;
        }
    }
    else if(lastDirection == 1)  // Was bullish
    {
        if(close1 <= lowerBand)
        {
            currentDirection = -1; // Flip to bearish
            currentSupertrend = upperBand;
        }
        else
        {
            currentDirection = 1;  // Stay bullish
            currentSupertrend = MathMax(lowerBand, lastSupertrend);
        }
    }
    else  // Was bearish
    {
        if(close1 >= upperBand)
        {
            currentDirection = 1;  // Flip to bullish
            currentSupertrend = lowerBand;
        }
        else
        {
            currentDirection = -1; // Stay bearish
            currentSupertrend = MathMin(upperBand, lastSupertrend);
        }
    }

    //--- Check for flip
    if(currentDirection != lastDirection && lastDirection != 0)
    {
        if(currentDirection == 1 && InpPrintSignals)
        {
            Print(">>> BULLISH FLIP at ", TimeToString(TimeCurrent()), " | Price: ", close1, " | ST: ", currentSupertrend);
        }
        else if(currentDirection == -1 && InpPrintSignals)
        {
            Print(">>> BEARISH FLIP at ", TimeToString(TimeCurrent()), " | Price: ", close1, " | ST: ", currentSupertrend);
        }
    }

    //--- Update globals
    lastDirection = currentDirection;
    lastSupertrend = currentSupertrend;
}

//+------------------------------------------------------------------+
//| Check for trading signals                                        |
//+------------------------------------------------------------------+
void CheckSignals()
{
    //--- Don't enter if already in position
    if(PositionSelect(_Symbol))
        return;

    //--- Check for bullish flip
    if(lastDirection == 1 && InpAllowLong)
    {
        double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
        if(close1 > lastSupertrend)  // Confirmation
        {
            if(InpPrintSignals)
                Print("==> OPENING LONG at ", SymbolInfoDouble(_Symbol, SYMBOL_ASK));
            OpenPosition(ORDER_TYPE_BUY);
        }
    }

    //--- Check for bearish flip
    if(lastDirection == -1 && InpAllowShort)
    {
        double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
        if(close1 < lastSupertrend)  // Confirmation
        {
            if(InpPrintSignals)
                Print("==> OPENING SHORT at ", SymbolInfoDouble(_Symbol, SYMBOL_BID));
            OpenPosition(ORDER_TYPE_SELL);
        }
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

    double price = (orderType == ORDER_TYPE_BUY) ?
                   SymbolInfoDouble(_Symbol, SYMBOL_ASK) :
                   SymbolInfoDouble(_Symbol, SYMBOL_BID);

    //--- Calculate stop loss
    double slDistance = price * InpStopLossPercent / 100.0;
    double sl = (orderType == ORDER_TYPE_BUY) ? price - slDistance : price + slDistance;
    sl = NormalizeDouble(sl, _Digits);

    //--- Fill request
    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = InpLotSize;
    request.type = orderType;
    request.price = NormalizeDouble(price, _Digits);
    request.sl = sl;
    request.tp = 0;
    request.deviation = 50;
    request.magic = InpMagicNumber;
    request.comment = "ST Entry";
    request.type_filling = ORDER_FILLING_FOK;

    //--- Send order
    if(!OrderSend(request, result))
    {
        Print("ERROR: OrderSend failed: ", GetLastError());
        Print("Request: price=", request.price, " sl=", request.sl, " lot=", request.volume);
        return;
    }

    if(result.retcode == TRADE_RETCODE_DONE)
    {
        Print("SUCCESS: Position opened | Type: ", (orderType == ORDER_TYPE_BUY ? "BUY" : "SELL"),
              " | Price: ", price, " | SL: ", sl, " | Lot: ", InpLotSize);
    }
    else
    {
        Print("ERROR: Order failed | Retcode: ", result.retcode, " | Comment: ", result.comment);
    }
}

//+------------------------------------------------------------------+
//| Manage existing positions                                        |
//+------------------------------------------------------------------+
void ManagePositions()
{
    if(!PositionSelect(_Symbol))
        return;

    long posType = PositionGetInteger(POSITION_TYPE);

    //--- Close on opposite signal
    if(posType == POSITION_TYPE_BUY && lastDirection == -1)
    {
        if(InpPrintSignals)
            Print("==> CLOSING LONG on bearish flip");
        ClosePosition("ST Reverse");
    }
    else if(posType == POSITION_TYPE_SELL && lastDirection == 1)
    {
        if(InpPrintSignals)
            Print("==> CLOSING SHORT on bullish flip");
        ClosePosition("ST Reverse");
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

    double currentPrice = (posType == POSITION_TYPE_BUY) ?
                          SymbolInfoDouble(_Symbol, SYMBOL_BID) :
                          SymbolInfoDouble(_Symbol, SYMBOL_ASK);

    double profitPercent = 0;
    if(posType == POSITION_TYPE_BUY)
        profitPercent = ((currentPrice - posOpenPrice) / posOpenPrice) * 100.0;
    else
        profitPercent = ((posOpenPrice - currentPrice) / posOpenPrice) * 100.0;

    //--- Check activation
    if(profitPercent >= InpTrailActivation)
    {
        double newSL = 0;

        if(posType == POSITION_TYPE_BUY)
        {
            newSL = currentPrice * (1 - InpTrailOffset / 100.0);
            newSL = NormalizeDouble(newSL, _Digits);

            if(newSL > currentSL + SymbolInfoDouble(_Symbol, SYMBOL_POINT) * 10)
            {
                ModifyPosition(newSL, 0);
            }
        }
        else
        {
            newSL = currentPrice * (1 + InpTrailOffset / 100.0);
            newSL = NormalizeDouble(newSL, _Digits);

            if(newSL < currentSL - SymbolInfoDouble(_Symbol, SYMBOL_POINT) * 10 || currentSL == 0)
            {
                ModifyPosition(newSL, 0);
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Modify position                                                   |
//+------------------------------------------------------------------+
void ModifyPosition(double sl, double tp)
{
    MqlTradeRequest request;
    MqlTradeResult result;
    ZeroMemory(request);
    ZeroMemory(result);

    long ticket = PositionGetInteger(POSITION_TICKET);

    request.action = TRADE_ACTION_SLTP;
    request.position = ticket;
    request.symbol = _Symbol;
    request.sl = sl;
    request.tp = tp;
    request.magic = InpMagicNumber;

    if(OrderSend(request, result))
    {
        if(result.retcode == TRADE_RETCODE_DONE && InpPrintSignals)
        {
            Print("Position modified | SL: ", sl);
        }
    }
}

//+------------------------------------------------------------------+
//| Close position                                                    |
//+------------------------------------------------------------------+
void ClosePosition(string comment)
{
    MqlTradeRequest request;
    MqlTradeResult result;
    ZeroMemory(request);
    ZeroMemory(result);

    long ticket = PositionGetInteger(POSITION_TICKET);
    long posType = PositionGetInteger(POSITION_TYPE);
    double volume = PositionGetDouble(POSITION_VOLUME);

    request.action = TRADE_ACTION_DEAL;
    request.position = ticket;
    request.symbol = _Symbol;
    request.volume = volume;
    request.type = (posType == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
    request.price = (posType == POSITION_TYPE_BUY) ?
                    SymbolInfoDouble(_Symbol, SYMBOL_BID) :
                    SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    request.deviation = 50;
    request.magic = InpMagicNumber;
    request.comment = comment;
    request.type_filling = ORDER_FILLING_FOK;

    if(!OrderSend(request, result))
    {
        Print("ERROR: Close failed: ", GetLastError());
        return;
    }

    if(result.retcode == TRADE_RETCODE_DONE)
    {
        Print("Position closed | Comment: ", comment);
    }
}

//+------------------------------------------------------------------+
//| Update display                                                    |
//+------------------------------------------------------------------+
void UpdateDisplay()
{
    string info = "\n====== SIMPLE SUPERTREND ======\n";
    info += "Trend: " + (lastDirection == 1 ? "BULLISH" : lastDirection == -1 ? "BEARISH" : "INIT") + "\n";
    info += "ST Level: " + DoubleToString(lastSupertrend, _Digits) + "\n";

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

    info += "\nATR Period: " + IntegerToString(InpATRPeriod) + "\n";
    info += "ATR Multi: " + DoubleToString(InpATRMultiplier, 1) + "\n";
    info += "Lot: " + DoubleToString(InpLotSize, 2) + "\n";

    Comment(info);
}
//+------------------------------------------------------------------+
