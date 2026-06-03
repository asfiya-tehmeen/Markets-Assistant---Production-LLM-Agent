"""Seed finance/markets documents for the knowledge base.

Short, self-contained chunks: a glossary, a small FAQ, and basic regulatory concepts.
Kept factual and definitional — deliberately NOT personalized advice or predictions.
"""

SEED_DOCS: list[dict[str, str]] = [
    # --- Glossary ---
    {"id": "g-market-cap", "title": "Market capitalisation", "category": "glossary",
     "text": "Market capitalisation (market cap) is the total value of an asset's circulating "
             "supply: current price multiplied by the number of units in circulation. For crypto, "
             "market cap = price x circulating supply. It is a rough size measure, not a measure of "
             "money invested."},
    {"id": "g-liquidity", "title": "Liquidity", "category": "glossary",
     "text": "Liquidity describes how easily an asset can be bought or sold without moving its "
             "price. High liquidity means tight bid-ask spreads and large order books; low liquidity "
             "means trades can cause large price swings (slippage)."},
    {"id": "g-volatility", "title": "Volatility", "category": "glossary",
     "text": "Volatility measures how much an asset's price fluctuates over time, usually as the "
             "standard deviation of returns. Higher volatility means larger and more frequent price "
             "swings and is a common proxy for risk."},
    {"id": "g-spread", "title": "Bid-ask spread", "category": "glossary",
     "text": "The bid-ask spread is the difference between the highest price buyers will pay (bid) "
             "and the lowest price sellers will accept (ask). A narrow spread indicates a liquid, "
             "competitive market; a wide spread indicates illiquidity or uncertainty."},
    {"id": "g-slippage", "title": "Slippage", "category": "glossary",
     "text": "Slippage is the difference between the expected price of a trade and the price at "
             "which it actually executes. It is larger for big orders in illiquid markets and during "
             "fast-moving conditions."},
    {"id": "g-pnl", "title": "Profit and loss (P/L)", "category": "glossary",
     "text": "Profit and loss (P/L) is the gain or loss on a position. For a long position, P/L = "
             "(exit price - entry price) x quantity. For a short, the sign is reversed. Unrealised "
             "P/L is mark-to-market on an open position; realised P/L is locked in after closing."},
    {"id": "g-long-short", "title": "Long vs short", "category": "glossary",
     "text": "Going long means buying an asset expecting its price to rise. Going short means "
             "selling a borrowed asset expecting to buy it back cheaper; shorts profit when the "
             "price falls and have theoretically unlimited loss if it rises."},
    {"id": "g-leverage", "title": "Leverage and margin", "category": "glossary",
     "text": "Leverage uses borrowed funds to increase position size relative to capital. Margin is "
             "the collateral posted. Leverage amplifies both gains and losses; if the price moves "
             "against a leveraged position past the maintenance margin, it can be liquidated."},
    {"id": "g-liquidation", "title": "Liquidation", "category": "glossary",
     "text": "Liquidation is the forced closing of a leveraged position by an exchange when the "
             "trader's margin can no longer cover losses. It locks in the loss and can occur "
             "automatically and rapidly during volatile moves."},
    {"id": "g-order-types", "title": "Market vs limit orders", "category": "glossary",
     "text": "A market order executes immediately at the best available price, prioritising speed "
             "over price. A limit order executes only at a specified price or better, prioritising "
             "price over certainty of execution."},
    {"id": "g-stop-loss", "title": "Stop-loss order", "category": "glossary",
     "text": "A stop-loss is an order that triggers a market or limit order once the price reaches a "
             "set level, used to cap losses on a position. Stops are not guaranteed fills and can "
             "slip in fast markets."},
    {"id": "g-position-size", "title": "Position sizing", "category": "glossary",
     "text": "Position sizing decides how much to allocate to a trade. A common risk-based method "
             "sizes the position so that hitting the stop-loss loses only a fixed percentage of the "
             "account: units = (account x risk%) / (entry price - stop price)."},
    {"id": "g-stablecoin", "title": "Stablecoin", "category": "glossary",
     "text": "A stablecoin is a cryptocurrency designed to hold a stable value, usually pegged to a "
             "fiat currency like the US dollar. Pegs can be backed by reserves (e.g. USDC, USDT) or "
             "maintained algorithmically; algorithmic pegs have historically been prone to failure."},
    {"id": "g-defi", "title": "Decentralised finance (DeFi)", "category": "glossary",
     "text": "Decentralised finance (DeFi) refers to financial services built on public blockchains "
             "using smart contracts, such as lending, borrowing, and trading on decentralised "
             "exchanges, without a central intermediary."},
    {"id": "g-amm", "title": "Automated market maker (AMM)", "category": "glossary",
     "text": "An automated market maker (AMM) is a decentralised exchange design that prices assets "
             "with a formula against pooled liquidity rather than an order book. Liquidity providers "
             "deposit assets and earn fees but bear impermanent loss."},
    {"id": "g-impermanent-loss", "title": "Impermanent loss", "category": "glossary",
     "text": "Impermanent loss is the value a liquidity provider gives up versus simply holding the "
             "assets, caused by price divergence between the two pooled tokens. It becomes permanent "
             "if the provider withdraws while prices remain diverged."},
    {"id": "g-gas", "title": "Gas fees", "category": "glossary",
     "text": "Gas is the fee paid to have a transaction processed on a blockchain such as Ethereum. "
             "Gas prices rise with network congestion and fall when demand for block space is low."},
    {"id": "g-cold-wallet", "title": "Custody: hot vs cold wallets", "category": "glossary",
     "text": "A hot wallet is connected to the internet and convenient but more exposed to hacks. A "
             "cold wallet is kept offline (e.g. hardware device) for stronger security. 'Not your "
             "keys, not your coins' refers to the custody risk of leaving assets on an exchange."},

    # --- FAQ ---
    {"id": "faq-what-is-crypto", "title": "What is cryptocurrency?", "category": "faq",
     "text": "Cryptocurrency is a digital asset that uses cryptography and a distributed ledger "
             "(blockchain) to record ownership and transfers without a central authority. Bitcoin "
             "was the first; thousands of others now exist with varied designs and uses."},
    {"id": "faq-spot-vs-futures", "title": "Spot vs futures trading", "category": "faq",
     "text": "Spot trading exchanges an asset for immediate delivery at the current price. Futures "
             "are contracts to buy or sell at a set price on a future date and are often leveraged; "
             "perpetual futures have no expiry and use a funding rate to track spot."},
    {"id": "faq-how-price-set", "title": "How are crypto prices determined?", "category": "faq",
     "text": "Crypto prices are set by supply and demand across exchanges. The quoted price reflects "
             "the most recent trades; aggregators average across venues. Prices can differ slightly "
             "between exchanges due to liquidity and regional demand."},
    {"id": "faq-diversification", "title": "What is diversification?", "category": "faq",
     "text": "Diversification spreads capital across different assets so that no single position "
             "dominates risk. It is a general risk-management concept; it reduces idiosyncratic risk "
             "but does not eliminate market-wide risk."},

    # --- Regulatory / compliance concepts ---
    {"id": "reg-kyc-aml", "title": "KYC and AML", "category": "regulatory",
     "text": "Know Your Customer (KYC) and Anti-Money-Laundering (AML) rules require regulated "
             "exchanges to verify customer identity and monitor transactions to detect illicit "
             "activity. Most centralised exchanges require KYC before trading or withdrawing."},
    {"id": "reg-securities", "title": "Are tokens securities?", "category": "regulatory",
     "text": "Whether a crypto token is a security depends on jurisdiction and facts. In the US, "
             "regulators often apply the Howey test, which asks whether there is an investment of "
             "money in a common enterprise with an expectation of profit from others' efforts. This "
             "is a legal determination, not investment advice."},
    {"id": "reg-mica", "title": "EU MiCA regulation", "category": "regulatory",
     "text": "The EU's Markets in Crypto-Assets (MiCA) regulation creates a harmonised framework for "
             "crypto-asset issuers and service providers across the EU, covering authorisation, "
             "stablecoin rules, and consumer protection."},
    {"id": "reg-tax-general", "title": "Crypto and taxes (general)", "category": "regulatory",
     "text": "In many jurisdictions, disposing of crypto (selling, swapping, or spending) can be a "
             "taxable event and may trigger capital gains. Rules vary widely by country and change "
             "over time; specific tax treatment should be confirmed with a qualified professional."},
    {"id": "reg-investor-protection", "title": "Investor protection limits in crypto", "category": "regulatory",
     "text": "Crypto assets often lack the deposit insurance and investor-protection schemes that "
             "cover bank deposits or regulated brokerage accounts. If an exchange fails or is "
             "hacked, recovery of funds is not guaranteed."},
    {"id": "reg-not-advice", "title": "Educational information vs financial advice", "category": "regulatory",
     "text": "Explaining how a financial instrument works is educational information. Recommending "
             "whether a specific person should buy, sell, or hold an asset is regulated financial "
             "advice and generally requires a licensed professional who knows the client's "
             "circumstances."},
]
