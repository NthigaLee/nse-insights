# TradingView Price Chart — Notes

## How it works

The live share price chart is embedded using the **TradingView Advanced Chart widget** (`tv.js`).

- `tv.js` is loaded once from `https://s3.tradingview.com/tv.js` in `<head>`
- When a company is selected, `initTradingViewChart(ticker)` in `app.js` is called
- The inner container `div` is replaced (to force a clean widget reset) and a new `TradingView.widget({...})` instance is created
- The widget renders inside `#tradingview-chart-container` → `#tradingview_widget_inner`

## Ticker format for NSE Kenya stocks

All NSE Kenya stocks use the exchange prefix `NSEKE:` on TradingView.

| Our ticker | TradingView symbol |
|-----------|-------------------|
| ABSA      | NSEKE:ABSA        |
| COOP      | NSEKE:COOP        |
| DTB       | NSEKE:DTB         |
| EQTY      | NSEKE:EQTY        |
| KCB       | NSEKE:KCB         |
| NCBA      | NSEKE:NCBA        |
| SCBK      | NSEKE:SCBK        |
| SCOM      | NSEKE:SCOM        |

**Important:** Safaricom trades as `SCOM` on NSE (not `SAFARICOM`), so the TradingView symbol is `NSEKE:SCOM`.

## Adding a new company

1. Add the company to `NSE_COMPANIES` in `data.js`
2. Add its ticker mapping to `NSEKE_TICKERS` in `app.js`:
   ```js
   TICK: 'NSEKE:TICK',
   ```
3. If the ticker isn't in `NSEKE_TICKERS`, it falls back to `NSEKE:<ticker>` automatically

## Known limitations

- **Price data delay:** TradingView data for NSE Kenya stocks may be delayed 15–30 minutes depending on market hours and data provider.
- **No direct price API access:** The TradingView widget runs in a cross-origin iframe. The parent page cannot read the current price or % change from it. Therefore the header price block shows "Live on chart" instead of a numeric price.
- **Widget reset:** Changing companies destroys and re-creates the widget (by replacing the inner div). This causes a brief flash/reload of the chart.
- **Internet required:** The widget requires a live internet connection to load. If `tv.js` fails to load, an error message is shown inside the chart container.
- **Theme:** The widget uses `theme: "dark"` to match the app's dark theme (`#0f172a` background). TradingView dark theme uses `#131722` internally — close enough.
- **allow_symbol_change: false:** The TradingView toolbar symbol search is disabled. Company switching is done exclusively via the app's company selector.
