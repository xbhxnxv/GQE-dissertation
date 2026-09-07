import yfinance as yf
import pandas as pd
import time
import os

# ─────────────────────────────────────────────────────────────────
# TOP 100 INDIAN COMPANIES — NIFTY 100 CONSTITUENTS
# Grouped by sector for easy reference
# All use .NS suffix = NSE (National Stock Exchange)
# ─────────────────────────────────────────────────────────────────

COMPANIES = {

    # ── BANKING ──────────────────────────────────────────────────
    "HDFCBANK.NS":    "HDFC Bank",
    "ICICIBANK.NS":   "ICICI Bank",
    "SBIN.NS":        "State Bank of India",
    "KOTAKBANK.NS":   "Kotak Mahindra Bank",
    "AXISBANK.NS":    "Axis Bank",
    "INDUSINDBK.NS":  "IndusInd Bank",
    "BANKBARODA.NS":  "Bank of Baroda",
    "FEDERALBNK.NS":  "Federal Bank",
    "IDFCFIRSTB.NS":  "IDFC First Bank",
    "PNB.NS":         "Punjab National Bank",

    # ── FINANCIAL SERVICES / NBFC ────────────────────────────────
    "BAJFINANCE.NS":  "Bajaj Finance",
    "BAJAJFINSV.NS":  "Bajaj Finserv",
    "CHOLAFIN.NS":    "Cholamandalam Finance",
    "MUTHOOTFIN.NS":  "Muthoot Finance",
    "SHRIRAMFIN.NS":  "Shriram Finance",
    "HDFCLIFE.NS":    "HDFC Life Insurance",
    "SBILIFE.NS":     "SBI Life Insurance",
    "ICICIGI.NS":     "ICICI Lombard General Insurance",
    "LICI.NS":        "Life Insurance Corporation",
    "NUVAMA.NS":      "Nuvama Wealth Management",

    # ── FINTECH / PAYMENTS / CAPITAL MARKETS ─────────────────────
    "PAYTM.NS":       "Paytm (One 97 Communications)",
    "POLICYBZR.NS":   "PB Fintech (PolicyBazaar)",
    "ANGELONE.NS":    "Angel One",
    "CDSL.NS":        "Central Depository Services",
    "BSE.NS":         "BSE Ltd",

    # ── IT & TECHNOLOGY ──────────────────────────────────────────
    "TCS.NS":         "Tata Consultancy Services",
    "INFY.NS":        "Infosys",
    "WIPRO.NS":       "Wipro",
    "HCLTECH.NS":     "HCL Technologies",
    "TECHM.NS":       "Tech Mahindra",
    "LTIM.NS":        "LTIMindtree",
    "PERSISTENT.NS":  "Persistent Systems",
    "MPHASIS.NS":     "Mphasis",
    "COFORGE.NS":     "Coforge",
    "OFSS.NS":        "Oracle Financial Services",

    # ── ENERGY & OIL ─────────────────────────────────────────────
    "RELIANCE.NS":    "Reliance Industries",
    "ONGC.NS":        "Oil & Natural Gas Corporation",
    "IOC.NS":         "Indian Oil Corporation",
    "BPCL.NS":        "Bharat Petroleum",
    "POWERGRID.NS":   "Power Grid Corporation",
    "NTPC.NS":        "NTPC Ltd",
    "ADANIGREEN.NS":  "Adani Green Energy",
    "ADANIPORTS.NS":  "Adani Ports",
    "ADANIENT.NS":    "Adani Enterprises",
    "TATAPOWER.NS":   "Tata Power",

    # ── AUTOMOBILE ───────────────────────────────────────────────
    "MARUTI.NS":      "Maruti Suzuki",
    "TATAMOTORS.NS":  "Tata Motors",
    "M&M.NS":         "Mahindra & Mahindra",
    "BAJAJ-AUTO.NS":  "Bajaj Auto",
    "EICHERMOT.NS":   "Eicher Motors (Royal Enfield)",
    "HEROMOTOCO.NS":  "Hero MotoCorp",
    "TVSMOTORS.NS":   "TVS Motor Company",
    "ASHOKLEY.NS":    "Ashok Leyland",
    "ESCORTS.NS":     "Escorts Kubota",
    "BOSCHLTD.NS":    "Bosch India",

    # ── FMCG & CONSUMER ──────────────────────────────────────────
    "HINDUNILVR.NS":  "Hindustan Unilever",
    "ITC.NS":         "ITC Ltd",
    "NESTLEIND.NS":   "Nestle India",
    "BRITANNIA.NS":   "Britannia Industries",
    "DABUR.NS":       "Dabur India",
    "MARICO.NS":      "Marico",
    "COLPAL.NS":      "Colgate-Palmolive India",
    "GODREJCP.NS":    "Godrej Consumer Products",
    "EMAMILTD.NS":    "Emami Ltd",
    "TATACONSUM.NS":  "Tata Consumer Products",

    # ── PHARMA & HEALTHCARE ───────────────────────────────────────
    "SUNPHARMA.NS":   "Sun Pharmaceutical",
    "DRREDDY.NS":     "Dr Reddy's Laboratories",
    "CIPLA.NS":       "Cipla",
    "DIVISLAB.NS":    "Divi's Laboratories",
    "APOLLOHOSP.NS":  "Apollo Hospitals",
    "BIOCON.NS":      "Biocon",
    "AUROPHARMA.NS":  "Aurobindo Pharma",
    "TORNTPHARM.NS":  "Torrent Pharmaceuticals",
    "LUPIN.NS":       "Lupin",
    "ALKEM.NS":       "Alkem Laboratories",

    # ── METALS & MINING ──────────────────────────────────────────
    "TATASTEEL.NS":   "Tata Steel",
    "JSWSTEEL.NS":    "JSW Steel",
    "HINDALCO.NS":    "Hindalco Industries",
    "COALINDIA.NS":   "Coal India",
    "VEDL.NS":        "Vedanta Ltd",
    "SAIL.NS":        "Steel Authority of India",
    "NMDC.NS":        "NMDC Ltd",
    "JINDALSTEL.NS":  "Jindal Steel & Power",
    "NATIONALUM.NS":  "National Aluminium Company",
    "APLAPOLLO.NS":   "APL Apollo Tubes",

    # ── INFRASTRUCTURE & CEMENT ──────────────────────────────────
    "ULTRACEMCO.NS":  "UltraTech Cement",
    "GRASIM.NS":      "Grasim Industries",
    "AMBUJACEM.NS":   "Ambuja Cements",
    "ACC.NS":         "ACC Ltd",
    "SHREECEM.NS":    "Shree Cement",
    "LT.NS":          "Larsen & Toubro",
    "LTTS.NS":        "L&T Technology Services",
    "SIEMENS.NS":     "Siemens India",
    "ABB.NS":         "ABB India",
    "CUMMINSIND.NS":  "Cummins India",

    # ── TELECOM & DIGITAL ─────────────────────────────────────────
    "BHARTIARTL.NS":  "Bharti Airtel",
    "IDEA.NS":        "Vodafone Idea",
    "INDUSTOWER.NS":  "Indus Towers",
    "ZOMATO.NS":      "Zomato",
    "NYKAA.NS":       "FSN E-Commerce (Nykaa)",

    # ── CONSUMER DURABLES / OTHERS ────────────────────────────────
    "TITAN.NS":       "Titan Company",
    "ASIANPAINT.NS":  "Asian Paints",
    "PIDILITIND.NS":  "Pidilite Industries",
    "BERGEPAINT.NS":  "Berger Paints",
    "HAVELLS.NS":     "Havells India",
    "DIXON.NS":       "Dixon Technologies",
    "VOLTAS.NS":      "Voltas",
    "CROMPTON.NS":    "Crompton Greaves Consumer",
    "POLYCAB.NS":     "Polycab India",
    "WHIRLPOOL.NS":   "Whirlpool India",
}

# ─────────────────────────────────────────────────────────────────
# DOWNLOAD ALL STOCK PRICES
# ─────────────────────────────────────────────────────────────────

def download_all(start="2019-01-01", end="2024-12-31", output_folder="01_data/financial/"):
    os.makedirs(output_folder, exist_ok=True)

    tickers = list(COMPANIES.keys())
    names   = list(COMPANIES.values())

    print(f"Downloading {len(tickers)} companies from NSE...")
    print(f"Date range: {start} to {end}\n")

    # Download all at once (faster than one by one)
    data = yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=True,
        progress=True
    )

    # Save full multi-ticker dataset
    close_prices = data["Close"]
    close_prices.to_csv(f"{output_folder}all_close_prices.csv")
    print(f"\nSaved: {output_folder}all_close_prices.csv")
    print(f"Shape: {close_prices.shape} (rows=trading days, cols=companies)")

    # Calculate daily returns
    daily_returns = close_prices.pct_change().dropna()
    daily_returns.to_csv(f"{output_folder}all_daily_returns.csv")
    print(f"Saved: {output_folder}all_daily_returns.csv")

    # Download NIFTY 100 as market benchmark
    print("\nDownloading NIFTY 100 benchmark (^CNX100)...")
    nifty = yf.download("^CNX100", start=start, end=end,
                        auto_adjust=True, progress=False)
    nifty["market_return"] = nifty["Close"].pct_change()
    nifty.to_csv(f"{output_folder}nifty100_benchmark.csv")
    print(f"Saved: {output_folder}nifty100_benchmark.csv")

    # Also download NIFTY 50 as secondary benchmark
    nifty50 = yf.download("^NSEI", start=start, end=end,
                          auto_adjust=True, progress=False)
    nifty50["market_return"] = nifty50["Close"].pct_change()
    nifty50.to_csv(f"{output_folder}nifty50_benchmark.csv")
    print(f"Saved: {output_folder}nifty50_benchmark.csv")

    # Save company master list
    master = pd.DataFrame({
        "ticker":  list(COMPANIES.keys()),
        "company": list(COMPANIES.values()),
        "exchange": "NSE"
    })
    master["sector"] = [
        "Banking","Banking","Banking","Banking","Banking",
        "Banking","Banking","Banking","Banking","Banking",
        "FinServ","FinServ","FinServ","FinServ","FinServ",
        "Insurance","Insurance","Insurance","Insurance","FinServ",
        "FinTech","FinTech","FinTech","FinTech","FinTech",
        "IT","IT","IT","IT","IT","IT","IT","IT","IT","IT",
        "Energy","Energy","Energy","Energy","Energy",
        "Energy","Energy","Energy","Energy","Energy",
        "Auto","Auto","Auto","Auto","Auto",
        "Auto","Auto","Auto","Auto","Auto",
        "FMCG","FMCG","FMCG","FMCG","FMCG",
        "FMCG","FMCG","FMCG","FMCG","FMCG",
        "Pharma","Pharma","Pharma","Pharma","Pharma",
        "Pharma","Pharma","Pharma","Pharma","Pharma",
        "Metals","Metals","Metals","Metals","Metals",
        "Metals","Metals","Metals","Metals","Metals",
        "Infra","Infra","Infra","Infra","Infra",
        "Infra","Infra","Infra","Infra","Infra",
        "Telecom","Telecom","Telecom","Digital","Digital",
        "Consumer","Consumer","Consumer","Consumer","Consumer",
        "Consumer","Consumer","Consumer","Consumer","Consumer",
    ]
    master.to_csv(f"{output_folder}company_master.csv", index=False)
    print(f"Saved: {output_folder}company_master.csv")

    # Summary report
    print("\n" + "="*50)
    print("DOWNLOAD SUMMARY")
    print("="*50)
    available = close_prices.dropna(how='all', axis=1).columns.tolist()
    missing   = [t for t in tickers if t not in available]
    print(f"Successfully downloaded: {len(available)} companies")
    if missing:
        print(f"Failed / no data:        {len(missing)} companies")
        for m in missing:
            print(f"   - {m} ({COMPANIES[m]})")
    print(f"\nFiles saved to: {output_folder}")
    return close_prices, daily_returns

# ─────────────────────────────────────────────────────────────────
# HOW TO USE IN YOUR DISSERTATION NOTEBOOKS
# ─────────────────────────────────────────────────────────────────
#
# 1. Run this script once to download everything:
#    python india_top100_download.py
#
# 2. In your event study notebook, load like this:
#
#    import pandas as pd
#    returns = pd.read_csv("01_data/financial/all_daily_returns.csv",
#                          index_col=0, parse_dates=True)
#    market  = pd.read_csv("01_data/financial/nifty100_benchmark.csv",
#                          index_col=0, parse_dates=True)
#
# 3. For a single company:
#    hdfc_returns = returns["HDFCBANK.NS"].dropna()
#
# 4. For sector-level analysis:
#    master  = pd.read_csv("01_data/financial/company_master.csv")
#    banking = master[master["sector"]=="Banking"]["ticker"].tolist()
#    banking_returns = returns[banking]
#
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    close_prices, daily_returns = download_all(
        start="2019-01-01",
        end="2024-12-31",
        output_folder="01_data/financial/"
    )
    print("\nDone. All data ready for your GQE dissertation.")
