//+------------------------------------------------------------------+
//|                                            Force_Trade_Test.mq5 |
//|                          EA Test - FORCE open position every 10 bars|
//+------------------------------------------------------------------+
#property copyright "Force Trade Test EA"
#property version   "1.00"
#property description "EA ini PASTI trade - untuk test MT5 settings"
#property strict

//--- Input Parameters
input double InpLotSize = 0.01;       // Lot Size (SMALL for testing)
input int InpBarsToTrade = 10;        // Open position every X bars
input int InpMagicNumber = 99999;     // Magic Number

//--- Global Variables
datetime lastBarTime = 0;
int barCounter = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("====================================================");
    Print("FORCE TRADE TEST EA - INITIALIZED");
    Print("This EA will FORCE open a position every ", InpBarsToTrade, " bars");
    Print("Lot Size: ", InpLotSize);
    Print("Symbol: ", _Symbol);
    Print("====================================================");

    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    //--- Check for new bar
    datetime currentBarTime = iTime(_Symbol, PERIOD_CURRENT, 0);
    if(currentBarTime == lastBarTime)
        return;

    lastBarTime = currentBarTime;
    barCounter++;

    Print("Bar #", barCounter, " | Time: ", TimeToString(currentBarTime));

    //--- Close any existing position first
    if(PositionSelect(_Symbol))
    {
        Print("Closing existing position...");
        ClosePosition();
    }

    //--- Open new position every X bars
    if(barCounter % InpBarsToTrade == 0)
    {
        Print(">>> FORCING BUY POSITION at bar ", barCounter);
        OpenBuy();
    }
}

//+------------------------------------------------------------------+
//| Open BUY position                                                |
//+------------------------------------------------------------------+
void OpenBuy()
{
    MqlTradeRequest request;
    MqlTradeResult result;
    ZeroMemory(request);
    ZeroMemory(result);

    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double sl = ask - (ask * 0.02); // 2% stop loss
    double tp = ask + (ask * 0.02); // 2% take profit

    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = InpLotSize;
    request.type = ORDER_TYPE_BUY;
    request.price = NormalizeDouble(ask, _Digits);
    request.sl = NormalizeDouble(sl, _Digits);
    request.tp = NormalizeDouble(tp, _Digits);
    request.deviation = 50;
    request.magic = InpMagicNumber;
    request.comment = "Force Test";
    request.type_filling = ORDER_FILLING_FOK;

    if(!OrderSend(request, result))
    {
        Print("!!! OrderSend FAILED - Error: ", GetLastError());
        Print("!!! This means your MT5 settings block trading!");
        Print("!!! Check: Tools → Options → Expert Advisors");
        Print("!!! Enable: 'Allow automated trading'");
        return;
    }

    if(result.retcode == TRADE_RETCODE_DONE)
    {
        Print("*** SUCCESS! Position opened at ", ask);
        Print("*** SL: ", sl, " | TP: ", tp);
        Print("*** If you see this, your MT5 CAN trade!");
    }
    else
    {
        Print("!!! Order REJECTED - Retcode: ", result.retcode);
        Print("!!! Comment: ", result.comment);

        if(result.retcode == 10027) Print("!!! AutoTrading is DISABLED!");
        if(result.retcode == 10021) Print("!!! Not enough money!");
        if(result.retcode == 10018) Print("!!! Market is closed!");
    }
}

//+------------------------------------------------------------------+
//| Close position                                                    |
//+------------------------------------------------------------------+
void ClosePosition()
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
    request.comment = "Close Test";
    request.type_filling = ORDER_FILLING_FOK;

    OrderSend(request, result);
}
//+------------------------------------------------------------------+
