# Kurokage-2

Resale arbitrage analyzer — upload a photo of an item from Amazon bins, Facebook Marketplace, or Goodwill and instantly get eBay sold price history, active listing competition, and a profit estimate.

## How it works

1. You open the form on your phone and snap a photo
2. Gemini Vision identifies the item (brand, model, category, condition)
3. The workflow queries eBay for recent sold prices and active listings
4. You get a mobile-friendly report with a **BUY / MAYBE / PASS** verdict and net profit estimate

## Setup

### Prerequisites

- n8n self-hosted instance (Docker or VPS)
- Google Gemini API key — [get one free](https://aistudio.google.com/app/apikey)
- eBay Developer App ID — [register at eBay Developers Program](https://developer.ebay.com/my/keys)

### 1. Add environment variables

In your n8n `.env` file (or Settings > Environment Variables in the UI):

```
GEMINI_API_KEY=your_gemini_key_here
EBAY_APP_ID=your_ebay_app_id_here
```

### 2. Import the workflow

In n8n: **Workflows > Import from file** — select `src/workflows/resale-analyzer.json`

### 3. Activate

Click the toggle in the top-right of the workflow editor to activate it.

### 4. Use it

Open the **Photo Upload Form** trigger URL on your phone (shown on the trigger node). Fill in the item photo, how much it costs, and where you found it — then submit.

## Profit calculation

| Item | Formula |
|---|---|
| Revenue | Average of last 50 eBay sold prices |
| eBay fees | ~13.25% of sale price |
| Shipping estimate | $8.00 flat (adjust in the "Analyze & Score" node) |
| Net profit | Revenue − eBay fees − shipping − your cost |

**Verdict thresholds:**
- **BUY** → ROI > 50%
- **MAYBE** → ROI 20–50%
- **PASS** → ROI < 20%
- **LOW DATA** → fewer than 3 sold listings found

## Project layout

```
src/
  workflows/
    resale-analyzer.json   # n8n workflow — import this
.env.example               # required environment variables
```
