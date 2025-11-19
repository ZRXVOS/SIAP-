//+------------------------------------------------------------------+
//|                                              Test_Indicator.mq5 |
//|                                   Test apakah MT5 bisa run code |
//+------------------------------------------------------------------+
#property copyright "Test Indicator"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 2
#property indicator_plots   2

//--- Plot Supertrend
#property indicator_label1  "ST Up"
#property indicator_type1   DRAW_LINE
#property indicator_color1  clrLime
#property indicator_style1  STYLE_SOLID
#property indicator_width1  3

#property indicator_label2  "ST Down"
#property indicator_type2   DRAW_LINE
#property indicator_color2  clrRed
#property indicator_style2  STYLE_SOLID
#property indicator_width2  3

//--- Input parameters
input int InpATRPeriod = 12;        // ATR Period
input double InpATRMultiplier = 3.0; // ATR Multiplier

//--- Indicator buffers
double STUpBuffer[];
double STDownBuffer[];

//--- Global variables
int handleATR;

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
    //--- Create ATR indicator
    handleATR = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
    if(handleATR == INVALID_HANDLE)
    {
        Print("ERROR: Cannot create ATR indicator");
        return(INIT_FAILED);
    }

    //--- Set indicator buffers
    SetIndexBuffer(0, STUpBuffer, INDICATOR_DATA);
    SetIndexBuffer(1, STDownBuffer, INDICATOR_DATA);

    //--- Set empty value
    PlotIndexSetDouble(0, PLOT_EMPTY_VALUE, 0);
    PlotIndexSetDouble(1, PLOT_EMPTY_VALUE, 0);

    //--- Set indicator short name
    IndicatorSetString(INDICATOR_SHORTNAME, "Supertrend Test");

    Print("===========================================");
    Print("TEST INDICATOR INITIALIZED SUCCESSFULLY!");
    Print("Symbol: ", _Symbol);
    Print("ATR Period: ", InpATRPeriod);
    Print("ATR Multiplier: ", InpATRMultiplier);
    Print("===========================================");

    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Custom indicator iteration function                              |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
{
    //--- Get ATR values
    double atr[];
    ArraySetAsSeries(atr, true);

    if(CopyBuffer(handleATR, 0, 0, rates_total, atr) <= 0)
    {
        return(0);
    }

    //--- Calculate from start
    int start = prev_calculated > 1 ? prev_calculated - 1 : 1;

    //--- Main loop
    for(int i = start; i < rates_total && !IsStopped(); i++)
    {
        int idx = rates_total - 1 - i;

        double hl2 = (high[i] + low[i]) / 2.0;
        double upperBand = hl2 + (InpATRMultiplier * atr[idx]);
        double lowerBand = hl2 - (InpATRMultiplier * atr[idx]);

        //--- Simple Supertrend logic
        if(close[i] > upperBand)
        {
            STUpBuffer[i] = lowerBand;
            STDownBuffer[i] = 0;
        }
        else if(close[i] < lowerBand)
        {
            STUpBuffer[i] = 0;
            STDownBuffer[i] = upperBand;
        }
        else
        {
            //--- Keep previous state
            if(i > 0)
            {
                if(STUpBuffer[i-1] > 0)
                {
                    STUpBuffer[i] = lowerBand;
                    STDownBuffer[i] = 0;
                }
                else
                {
                    STUpBuffer[i] = 0;
                    STDownBuffer[i] = upperBand;
                }
            }
        }
    }

    //--- Print on new bar
    static datetime lastBar = 0;
    if(time[rates_total-1] != lastBar)
    {
        lastBar = time[rates_total-1];

        int last = rates_total - 1;
        string trend = STUpBuffer[last] > 0 ? "BULLISH" : "BEARISH";
        double stValue = STUpBuffer[last] > 0 ? STUpBuffer[last] : STDownBuffer[last];

        Print("NEW BAR: ", TimeToString(time[last]),
              " | Trend: ", trend,
              " | ST: ", DoubleToString(stValue, _Digits),
              " | Close: ", DoubleToString(close[last], _Digits));
    }

    return(rates_total);
}
//+------------------------------------------------------------------+
