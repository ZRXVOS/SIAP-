//+------------------------------------------------------------------+
//|                                      EA_Supertrend_Simple_V2.mq5 |
//|                                    GUARANTEED TO TRADE - V2      |
//|                              ULTRA SIMPLE - MAXIMUM DEBUGGING    |
//+------------------------------------------------------------------+
#property copyright "Simple Supertrend EA V2"
#property version   "2.00"
#property description "EA Supertrend Paling Sederhana - PASTI ADA TRANSAKSI!"
#property strict

//+------------------------------------------------------------------+
//| INPUT PARAMETERS - PENGATURAN EA                                 |
//+------------------------------------------------------------------+
input group "===== SUPERTREND SETTINGS ====="
input int InpATRPeriod = 12;              // ATR Period (12 = standard)
input double InpATRMultiplier = 3.0;      // ATR Multiplier (3.0 = standard)

input group "===== RISK MANAGEMENT ====="
input double InpLotSize = 0.02;           // Lot Size (0.02 = kecil untuk test)
input double InpStopLossPercent = 4.0;    // Stop Loss % (4% = dari V8)

input group "===== TRADING DIRECTION ====="
input bool InpAllowLong = true;           // Allow BUY (LONG) trades
input bool InpAllowShort = false;         // Allow SELL (SHORT) trades

input group "===== SYSTEM ====="
input int InpMagicNumber = 88888;         // Magic Number (ID untuk EA ini)

//+------------------------------------------------------------------+
//| GLOBAL VARIABLES - Variabel yang dipakai di seluruh EA          |
//+------------------------------------------------------------------+
int atrHandle;                  // Handle untuk ATR indicator
double atrBuffer[];             // Buffer untuk menyimpan nilai ATR

// Supertrend state
int trendDirection = 0;         // 1 = Bullish, -1 = Bearish, 0 = Not initialized
double supertrendValue = 0;     // Nilai Supertrend saat ini
datetime lastBarTime = 0;       // Waktu bar terakhir (untuk deteksi bar baru)

// Trading state
bool positionOpen = false;      // Apakah ada posisi terbuka?
long currentTicket = 0;         // Ticket number posisi saat ini

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("===============================================");
    Print("EA SUPERTREND SIMPLE V2 - STARTING");
    Print("===============================================");

    // Create ATR indicator
    atrHandle = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
    if(atrHandle == INVALID_HANDLE)
    {
        Print("ERROR: Gagal membuat ATR indicator!");
        Print("ERROR: Kemungkinan symbol atau timeframe tidak valid");
        return(INIT_FAILED);
    }

    // Set array as series (index 0 = newest)
    ArraySetAsSeries(atrBuffer, true);

    // Print configuration
    Print("KONFIGURASI EA:");
    Print("- Symbol: ", _Symbol);
    Print("- Timeframe: ", EnumToString(PERIOD_CURRENT));
    Print("- ATR Period: ", InpATRPeriod);
    Print("- ATR Multiplier: ", InpATRMultiplier);
    Print("- Lot Size: ", InpLotSize);
    Print("- Stop Loss: ", InpStopLossPercent, "%");
    Print("- Allow Long: ", InpAllowLong ? "YES" : "NO");
    Print("- Allow Short: ", InpAllowShort ? "YES" : "NO");
    Print("- Magic Number: ", InpMagicNumber);
    Print("===============================================");
    Print("EA INITIALIZED SUCCESSFULLY!");
    Print("Waiting for new bar to start trading...");
    Print("===============================================");

    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    // Release indicator handle
    if(atrHandle != INVALID_HANDLE)
        IndicatorRelease(atrHandle);

    // Clear chart comment
    Comment("");

    Print("===============================================");
    Print("EA SUPERTREND SIMPLE V2 - STOPPED");
    Print("Reason: ", reason);
    Print("===============================================");
}

//+------------------------------------------------------------------+
//| Expert tick function - Dipanggil setiap ada perubahan harga     |
//+------------------------------------------------------------------+
void OnTick()
{
    // Check for new bar
    datetime currentBarTime = iTime(_Symbol, PERIOD_CURRENT, 0);

    // Only process on new bar (bukan setiap tick)
    if(currentBarTime == lastBarTime)
    {
        UpdateDisplay(); // Update display saja
        return;
    }

    // New bar detected!
    lastBarTime = currentBarTime;
    Print("----------------------------------------");
    Print("NEW BAR: ", TimeToString(currentBarTime, TIME_DATE|TIME_MINUTES));

    // Update ATR values
    if(!UpdateIndicators())
    {
        Print("WARNING: Failed to update indicators, skipping this bar");
        return;
    }

    // Calculate Supertrend
    CalculateSupertrend();

    // Check for trading signals
    CheckForSignals();

    // Update display
    UpdateDisplay();
}

//+------------------------------------------------------------------+
//| Update indicator values                                          |
//+------------------------------------------------------------------+
bool UpdateIndicators()
{
    // Copy ATR buffer (ambil 3 bar terakhir)
    if(CopyBuffer(atrHandle, 0, 0, 3, atrBuffer) < 3)
    {
        Print("ERROR: Failed to copy ATR buffer");
        return false;
    }

    Print("ATR[1] = ", DoubleToString(atrBuffer[1], _Digits));
    return true;
}

//+------------------------------------------------------------------+
//| Calculate Supertrend indicator                                  |
//+------------------------------------------------------------------+
void CalculateSupertrend()
{
    // Get previous bar data (bar index 1 = previous closed bar)
    double high1 = iHigh(_Symbol, PERIOD_CURRENT, 1);
    double low1 = iLow(_Symbol, PERIOD_CURRENT, 1);
    double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);

    // Calculate HL/2 (average of high and low)
    double hl2 = (high1 + low1) / 2.0;

    // Calculate Supertrend bands
    double upperBand = hl2 + (InpATRMultiplier * atrBuffer[1]);
    double lowerBand = hl2 - (InpATRMultiplier * atrBuffer[1]);

    Print("Price Data: High=", high1, " Low=", low1, " Close=", close1);
    Print("HL/2 = ", hl2, " | ATR = ", atrBuffer[1]);
    Print("Upper Band = ", DoubleToString(upperBand, _Digits));
    Print("Lower Band = ", DoubleToString(lowerBand, _Digits));

    // Determine trend direction
    int previousDirection = trendDirection;

    // First time calculation
    if(trendDirection == 0)
    {
        if(close1 > hl2)
        {
            trendDirection = 1;  // Bullish
            supertrendValue = lowerBand;
            Print("INITIAL TREND: BULLISH");
        }
        else
        {
            trendDirection = -1; // Bearish
            supertrendValue = upperBand;
            Print("INITIAL TREND: BEARISH");
        }
    }
    // Currently bullish
    else if(trendDirection == 1)
    {
        // Check if price crossed below lower band
        if(close1 <= lowerBand)
        {
            trendDirection = -1; // Flip to bearish
            supertrendValue = upperBand;
            Print("*** TREND FLIP: BULLISH -> BEARISH ***");
            Print("*** Price ", close1, " crossed below ", lowerBand, " ***");
        }
        else
        {
            // Stay bullish, update supertrend
            supertrendValue = MathMax(lowerBand, supertrendValue);
            trendDirection = 1;
        }
    }
    // Currently bearish
    else if(trendDirection == -1)
    {
        // Check if price crossed above upper band
        if(close1 >= upperBand)
        {
            trendDirection = 1;  // Flip to bullish
            supertrendValue = lowerBand;
            Print("*** TREND FLIP: BEARISH -> BULLISH ***");
            Print("*** Price ", close1, " crossed above ", upperBand, " ***");
        }
        else
        {
            // Stay bearish, update supertrend
            supertrendValue = MathMin(upperBand, supertrendValue);
            trendDirection = -1;
        }
    }

    Print("Current Trend: ", (trendDirection == 1 ? "BULLISH" : "BEARISH"));
    Print("Supertrend Value: ", DoubleToString(supertrendValue, _Digits));

    // Check if trend flipped
    if(previousDirection != 0 && previousDirection != trendDirection)
    {
        Print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!");
        Print("!!! SUPERTREND FLIP DETECTED !!!");
        Print("!!! From ", (previousDirection == 1 ? "BULLISH" : "BEARISH"),
              " to ", (trendDirection == 1 ? "BULLISH" : "BEARISH"), " !!!");
        Print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!");
    }
}

//+------------------------------------------------------------------+
//| Check for trading signals                                        |
//+------------------------------------------------------------------+
void CheckForSignals()
{
    // Update position status
    positionOpen = PositionSelect(_Symbol);

    if(positionOpen)
    {
        Print("Position already open - checking for exit signal");
        CheckForExit();
        return;
    }

    Print("No position open - checking for entry signal");

    // Check for LONG entry (bullish signal)
    if(trendDirection == 1 && InpAllowLong)
    {
        Print(">>> LONG SIGNAL DETECTED <<<");
        Print(">>> Trend is BULLISH, opening BUY position...");
        OpenPosition(ORDER_TYPE_BUY);
    }
    // Check for SHORT entry (bearish signal)
    else if(trendDirection == -1 && InpAllowShort)
    {
        Print(">>> SHORT SIGNAL DETECTED <<<");
        Print(">>> Trend is BEARISH, opening SELL position...");
        OpenPosition(ORDER_TYPE_SELL);
    }
    else
    {
        if(trendDirection == 1 && !InpAllowLong)
            Print("LONG signal but LONG trades disabled in settings");
        else if(trendDirection == -1 && !InpAllowShort)
            Print("SHORT signal but SHORT trades disabled in settings");
    }
}

//+------------------------------------------------------------------+
//| Open new position                                                |
//+------------------------------------------------------------------+
void OpenPosition(ENUM_ORDER_TYPE orderType)
{
    MqlTradeRequest request;
    MqlTradeResult result;
    ZeroMemory(request);
    ZeroMemory(result);

    // Get current price
    double price = 0;
    if(orderType == ORDER_TYPE_BUY)
        price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    else
        price = SymbolInfoDouble(_Symbol, SYMBOL_BID);

    // Calculate stop loss
    double slDistance = price * InpStopLossPercent / 100.0;
    double sl = 0;
    if(orderType == ORDER_TYPE_BUY)
        sl = price - slDistance;
    else
        sl = price + slDistance;

    sl = NormalizeDouble(sl, _Digits);
    price = NormalizeDouble(price, _Digits);

    Print("Opening ", (orderType == ORDER_TYPE_BUY ? "BUY" : "SELL"), " position:");
    Print("- Entry Price: ", price);
    Print("- Stop Loss: ", sl, " (", InpStopLossPercent, "% away)");
    Print("- Lot Size: ", InpLotSize);

    // Prepare request
    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = InpLotSize;
    request.type = orderType;
    request.price = price;
    request.sl = sl;
    request.tp = 0; // No take profit
    request.deviation = 50;
    request.magic = InpMagicNumber;
    request.comment = "ST Simple V2";
    request.type_filling = ORDER_FILLING_FOK;

    // Send order
    if(!OrderSend(request, result))
    {
        Print("!!! ERROR: OrderSend failed !!!");
        Print("!!! Error code: ", GetLastError(), " !!!");
        return;
    }

    // Check result
    if(result.retcode == TRADE_RETCODE_DONE)
    {
        Print("========================================");
        Print("SUCCESS! Position opened successfully!");
        Print("Ticket: ", result.order);
        Print("Price: ", result.price);
        Print("Volume: ", result.volume);
        Print("========================================");
        currentTicket = result.order;
    }
    else
    {
        Print("!!! ORDER FAILED !!!");
        Print("!!! Retcode: ", result.retcode, " !!!");
        Print("!!! Comment: ", result.comment, " !!!");

        // Common error codes
        if(result.retcode == 10027)
            Print("!!! AutoTrading is DISABLED! Enable it in Tools->Options->Expert Advisors !!!");
        if(result.retcode == 10021)
            Print("!!! Not enough money! Reduce lot size or increase balance !!!");
        if(result.retcode == 10018)
            Print("!!! Market is closed! !!!");
    }
}

//+------------------------------------------------------------------+
//| Check for exit signal                                            |
//+------------------------------------------------------------------+
void CheckForExit()
{
    if(!PositionSelect(_Symbol))
        return;

    long posType = PositionGetInteger(POSITION_TYPE);

    // Close LONG on bearish flip
    if(posType == POSITION_TYPE_BUY && trendDirection == -1)
    {
        Print(">>> EXIT SIGNAL: Closing LONG on bearish flip");
        ClosePosition();
    }
    // Close SHORT on bullish flip
    else if(posType == POSITION_TYPE_SELL && trendDirection == 1)
    {
        Print(">>> EXIT SIGNAL: Closing SHORT on bullish flip");
        ClosePosition();
    }
}

//+------------------------------------------------------------------+
//| Close current position                                           |
//+------------------------------------------------------------------+
void ClosePosition()
{
    if(!PositionSelect(_Symbol))
        return;

    MqlTradeRequest request;
    MqlTradeResult result;
    ZeroMemory(request);
    ZeroMemory(result);

    long ticket = PositionGetInteger(POSITION_TICKET);
    long posType = PositionGetInteger(POSITION_TYPE);
    double volume = PositionGetDouble(POSITION_VOLUME);
    double profit = PositionGetDouble(POSITION_PROFIT);

    Print("Closing position...");
    Print("- Ticket: ", ticket);
    Print("- Type: ", (posType == POSITION_TYPE_BUY ? "BUY" : "SELL"));
    Print("- Volume: ", volume);
    Print("- Current Profit: ", profit);

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
    request.comment = "ST Exit";
    request.type_filling = ORDER_FILLING_FOK;

    if(!OrderSend(request, result))
    {
        Print("!!! ERROR: Failed to close position !!!");
        Print("!!! Error: ", GetLastError(), " !!!");
        return;
    }

    if(result.retcode == TRADE_RETCODE_DONE)
    {
        Print("========================================");
        Print("Position closed successfully!");
        Print("Final Profit: ", profit);
        Print("========================================");
        currentTicket = 0;
    }
    else
    {
        Print("!!! Close failed - Retcode: ", result.retcode, " !!!");
    }
}

//+------------------------------------------------------------------+
//| Update chart display                                             |
//+------------------------------------------------------------------+
void UpdateDisplay()
{
    string info = "\n";
    info += "========== EA SUPERTREND SIMPLE V2 ==========\n";
    info += "Time: " + TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES) + "\n";
    info += "\n";
    info += "TREND: " + (trendDirection == 1 ? "BULLISH ▲" : trendDirection == -1 ? "BEARISH ▼" : "INIT") + "\n";
    info += "Supertrend: " + DoubleToString(supertrendValue, _Digits) + "\n";
    info += "Current Price: " + DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_BID), _Digits) + "\n";
    info += "\n";

    if(PositionSelect(_Symbol))
    {
        long posType = PositionGetInteger(POSITION_TYPE);
        double posProfit = PositionGetDouble(POSITION_PROFIT);
        double posOpenPrice = PositionGetDouble(POSITION_PRICE_OPEN);

        info += "POSITION: " + (posType == POSITION_TYPE_BUY ? "LONG (BUY)" : "SHORT (SELL)") + "\n";
        info += "Entry: " + DoubleToString(posOpenPrice, _Digits) + "\n";
        info += "Profit: " + DoubleToString(posProfit, 2) + " USD\n";
    }
    else
    {
        info += "POSITION: None\n";
    }

    info += "\n";
    info += "Settings: ATR " + IntegerToString(InpATRPeriod) + ", Multi " + DoubleToString(InpATRMultiplier, 1) + "\n";
    info += "Lot: " + DoubleToString(InpLotSize, 2) + " | SL: " + DoubleToString(InpStopLossPercent, 1) + "%\n";
    info += "============================================\n";

    Comment(info);
}
//+------------------------------------------------------------------+
