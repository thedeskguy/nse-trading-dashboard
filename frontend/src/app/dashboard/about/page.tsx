export default function AboutPage() {
  return (
    <div className="space-y-10 max-w-3xl pb-16">
      <div>
        <h1 className="text-2xl font-bold">How It Works</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Methodology behind every signal, score, and prediction on this platform.
        </p>
      </div>

      {/* ── Technical Signals ───────────────────────────────────────── */}
      <section className="space-y-5">
        <SectionHeader
          label="01"
          title="Technical Signal Score"
          sub="Six indicators vote independently. Their points sum to a raw score that maps to a 0–100 confidence scale."
        />

        <div className="space-y-3">
          <Indicator
            name="RSI — Relative Strength Index"
            period="14-period"
            desc="Measures momentum by comparing average up-moves vs down-moves over 14 days. Values below 30 suggest the stock has been sold too aggressively (oversold); above 70 suggests it may be over-bought."
            rows={[
              { condition: "RSI < 30", label: "Oversold — Bullish", pts: "+15" },
              { condition: "30 ≤ RSI < 40", label: "Approaching Oversold", pts: "+8" },
              { condition: "40 ≤ RSI ≤ 60", label: "Neutral", pts: "0" },
              { condition: "60 < RSI ≤ 70", label: "Approaching Overbought", pts: "−8" },
              { condition: "RSI > 70", label: "Overbought — Bearish", pts: "−15" },
            ]}
          />

          <Indicator
            name="MACD — Moving Average Convergence Divergence"
            period="12/26 EMA · 9 signal"
            desc="Tracks the difference between a fast (12-day) and slow (26-day) exponential moving average. A crossover above the signal line is the classic buy trigger; crossing below is a sell trigger."
            rows={[
              { condition: "MACD crosses above signal line", label: "Bullish Crossover", pts: "+20" },
              { condition: "MACD crosses below signal line", label: "Bearish Crossover", pts: "−20" },
              { condition: "MACD above signal (no cross)", label: "Bullish", pts: "+10" },
              { condition: "MACD below signal (no cross)", label: "Bearish", pts: "−10" },
            ]}
          />

          <Indicator
            name="EMA Trend"
            period="9 · 21 · 50 · 200 day"
            desc="Counts how many of the four exponential moving averages sit below the current price. A stock trading above all four EMAs is in a strong uptrend across every timeframe."
            rows={[
              { condition: "Price above all 4 EMAs", label: "Strong Bullish", pts: "+20" },
              { condition: "Price above 3 of 4 EMAs", label: "Bullish", pts: "+15" },
              { condition: "Price above 2 of 4 EMAs", label: "Mildly Bullish", pts: "+10" },
              { condition: "Price above 1 of 4 EMAs", label: "Mildly Bearish", pts: "−10" },
              { condition: "Price below all 4 EMAs", label: "Strong Bearish", pts: "−20" },
            ]}
          />

          <Indicator
            name="Bollinger Bands"
            period="20-day · 2σ"
            desc="A 20-day moving average with bands drawn ±2 standard deviations above and below. Price near the lower band suggests exhaustion of sellers; near the upper band suggests exhaustion of buyers. A squeeze (bands contracting) warns of an impending breakout."
            rows={[
              { condition: "Price within 5% of lower band", label: "Oversold — Near Lower Band", pts: "+15" },
              { condition: "Price within 5% of upper band", label: "Overbought — Near Upper Band", pts: "−15" },
              { condition: "Bands contracting (squeeze)", label: "Breakout Pending", pts: "0" },
              { condition: "Price inside bands, no squeeze", label: "Neutral", pts: "0" },
            ]}
          />

          <Indicator
            name="Support & Resistance"
            period="Pivot-based"
            desc="Key horizontal levels derived from recent swing highs and lows. Price bouncing off support is bullish; breaking through support is bearish. The reverse applies to resistance."
            rows={[
              { condition: "Within 1% above support", label: "Near Support", pts: "+15" },
              { condition: "0.5–2% above support", label: "Bounced from Support", pts: "+10" },
              { condition: "Price above resistance", label: "Breakout Above Resistance", pts: "+10" },
              { condition: "Within 1% below resistance", label: "Near Resistance", pts: "−15" },
              { condition: "Price below support", label: "Broke Support", pts: "−10" },
            ]}
          />

          <Indicator
            name="OBV — On-Balance Volume"
            period="10-bar rolling slope"
            desc="Cumulates volume: adds it on up-days, subtracts on down-days. A 10-bar linear regression slope is compared against the price slope to detect divergences — rising OBV with falling price often precedes a reversal upward."
            rows={[
              { condition: "OBV slope up, price slope up", label: "OBV Confirming Uptrend", pts: "+15" },
              { condition: "OBV slope down, price slope down", label: "OBV Confirming Downtrend", pts: "−15" },
              { condition: "OBV slope up, price slope down", label: "Bullish OBV Divergence", pts: "+8" },
              { condition: "OBV slope down, price slope up", label: "Bearish OBV Divergence", pts: "−8" },
            ]}
          />
        </div>

        {/* Confidence formula */}
        <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
          <h3 className="font-semibold text-sm">Confidence Score Formula</h3>
          <p className="text-muted-foreground text-xs leading-relaxed">
            All six indicator scores are summed into a <strong className="text-foreground">raw score</strong> ranging
            from <strong className="text-foreground">−100</strong> (all indicators maximally bearish)
            to <strong className="text-foreground">+100</strong> (all maximally bullish).
            This is then linearly mapped to a 0–100 confidence scale:
          </p>
          <div className="bg-muted/50 rounded-xl p-4 font-mono text-xs text-center text-foreground">
            confidence = ((raw_score + 100) / 200) × 100
          </div>
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: "BUY", range: "confidence > 60", color: "text-buy", bg: "bg-buy/10 border-buy/20" },
              { label: "HOLD", range: "40 ≤ confidence ≤ 60", color: "text-hold", bg: "bg-hold/10 border-hold/20" },
              { label: "SELL", range: "confidence < 40", color: "text-sell", bg: "bg-sell/10 border-sell/20" },
            ].map(s => (
              <div key={s.label} className={`rounded-xl p-3 border text-center ${s.bg}`}>
                <div className={`font-bold text-base ${s.color}`}>{s.label}</div>
                <div className="text-[10px] text-muted-foreground mt-0.5">{s.range}</div>
              </div>
            ))}
          </div>
          <p className="text-muted-foreground text-xs leading-relaxed">
            <strong className="text-foreground">Stop-loss & target</strong> are calculated using
            ATR-14 (Average True Range over 14 days), which measures typical daily volatility.
            For BUY signals: stop = price − 1.5 × ATR, target = price + 3 × ATR.
            This gives a 2:1 reward-to-risk ratio.
          </p>
        </div>
      </section>

      {/* ── Fundamentals ─────────────────────────────────────────────── */}
      <section className="space-y-5">
        <SectionHeader
          label="02"
          title="Fundamental Analysis"
          sub="Five financial health dimensions plus analyst consensus, each scored out of a fixed maximum. Total out of 100."
        />

        <div className="bg-card border border-border rounded-2xl divide-y divide-border">
          {[
            {
              name: "PE Ratio (Price / Earnings)",
              max: "15 pts",
              desc: "Compares price to earnings per share. Lower PE generally means cheaper relative to earnings.",
              rows: [
                { condition: "PE < 15", pts: "15", label: "Excellent" },
                { condition: "15 ≤ PE < 25", pts: "12", label: "Good" },
                { condition: "25 ≤ PE < 40", pts: "8", label: "Fair" },
                { condition: "PE ≥ 40", pts: "2", label: "Expensive" },
              ],
            },
            {
              name: "ROE (Return on Equity)",
              max: "15 pts",
              desc: "Net profit divided by shareholder equity. Shows how efficiently the company uses investors' money.",
              rows: [
                { condition: "ROE > 20%", pts: "15", label: "Excellent" },
                { condition: "15% < ROE ≤ 20%", pts: "12", label: "Good" },
                { condition: "10% < ROE ≤ 15%", pts: "8", label: "Fair" },
                { condition: "ROE ≤ 10%", pts: "2", label: "Weak" },
              ],
            },
            {
              name: "Debt / Equity",
              max: "15 pts",
              desc: "Total borrowings relative to equity capital. Lower is generally safer. Expressed as a percentage in screener.in format.",
              rows: [
                { condition: "D/E < 30", pts: "15", label: "Low debt" },
                { condition: "30 ≤ D/E < 80", pts: "10", label: "Moderate" },
                { condition: "80 ≤ D/E < 150", pts: "5", label: "High" },
                { condition: "D/E ≥ 150", pts: "0", label: "Very High" },
              ],
            },
            {
              name: "Revenue Growth (YoY)",
              max: "15 pts",
              desc: "Year-on-year change in annual revenue. Consistent growth above inflation indicates a healthy business.",
              rows: [
                { condition: "Growth > 20%", pts: "15", label: "Strong" },
                { condition: "10% < Growth ≤ 20%", pts: "10", label: "Good" },
                { condition: "5% < Growth ≤ 10%", pts: "6", label: "Moderate" },
                { condition: "0% < Growth ≤ 5%", pts: "3", label: "Slow" },
                { condition: "Growth ≤ 0%", pts: "0", label: "Declining" },
              ],
            },
            {
              name: "Net Profit Margin",
              max: "15 pts",
              desc: "Net profit as a percentage of revenue. Higher margin means the company converts more of its sales into actual profit.",
              rows: [
                { condition: "Margin > 20%", pts: "15", label: "Excellent" },
                { condition: "12% < Margin ≤ 20%", pts: "10", label: "Good" },
                { condition: "5% < Margin ≤ 12%", pts: "6", label: "Fair" },
                { condition: "Margin ≤ 5%", pts: "2", label: "Thin" },
              ],
            },
            {
              name: "Analyst View",
              max: "25 pts",
              desc: "Consensus from sell-side analysts tracked by Yahoo Finance. Combines recommendation rating (BUY/HOLD/SELL) and analyst price target vs current price.",
              rows: [
                { condition: "Analyst rating: BUY / Strong Buy", pts: "+15", label: "Analyst view" },
                { condition: "Analyst rating: HOLD / Neutral", pts: "+8", label: "Analyst view" },
                { condition: "Price target upside > 15%", pts: "+10", label: "Target upside" },
                { condition: "Price target upside 0–15%", pts: "+5", label: "Modest upside" },
                { condition: "Analyst rating: SELL", pts: "0", label: "No points" },
              ],
            },
          ].map((cat) => (
            <div key={cat.name} className="p-5 space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-medium text-sm">{cat.name}</div>
                  <div className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{cat.desc}</div>
                </div>
                <span className="text-xs text-primary font-mono shrink-0">max {cat.max}</span>
              </div>
              <div className="grid grid-cols-2 gap-1.5">
                {cat.rows.map((r) => (
                  <div key={r.condition} className="bg-muted/40 rounded-lg px-3 py-1.5 flex justify-between items-center gap-2">
                    <span className="text-xs text-muted-foreground">{r.condition}</span>
                    <span className="text-xs font-mono font-semibold text-foreground shrink-0">{r.pts}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="bg-card border border-border rounded-2xl p-5 space-y-3">
          <h3 className="font-semibold text-sm">Overall Grade</h3>
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: "Strong", range: "Score ≥ 65", color: "text-buy", bg: "bg-buy/10 border-buy/20" },
              { label: "Fair", range: "45 ≤ Score < 65", color: "text-hold", bg: "bg-hold/10 border-hold/20" },
              { label: "Weak", range: "Score < 45", color: "text-sell", bg: "bg-sell/10 border-sell/20" },
            ].map(g => (
              <div key={g.label} className={`rounded-xl p-3 border text-center ${g.bg}`}>
                <div className={`font-bold text-base ${g.color}`}>{g.label}</div>
                <div className="text-[10px] text-muted-foreground mt-0.5">{g.range}</div>
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            <strong className="text-foreground">Data sources:</strong> screener.in is the primary source
            for Indian financial data (P/E, ROE, D/E, revenue, margins — sourced from BSE/NSE filings).
            Yahoo Finance supplements with analyst consensus, price targets, P/B ratio, and sector/industry classification.
          </p>
        </div>
      </section>

      {/* ── ML Prediction ────────────────────────────────────────────── */}
      <section className="space-y-5">
        <SectionHeader
          label="03"
          title="ML Prediction Model"
          sub="A Random Forest classifier trained fresh on each request, predicting whether tomorrow's closing price will be higher or lower than today's."
        />

        <div className="bg-card border border-border rounded-2xl p-5 space-y-5">
          <div className="space-y-2">
            <div className="text-sm font-medium">Algorithm</div>
            <div className="bg-muted/50 rounded-xl p-4 text-xs text-muted-foreground leading-relaxed space-y-1">
              <div><strong className="text-foreground">Random Forest Classifier</strong> — an ensemble of 100 decision trees.</div>
              <div>Each tree is trained on a random subset of data and features; their majority vote becomes the prediction.</div>
              <div className="mt-2 font-mono text-[11px] text-foreground/70">
                n_estimators=100 · max_depth=6 · min_samples_leaf=5 · random_state=42
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium">Training Data</div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Daily OHLCV from Yahoo Finance (default: 1 year of trading days, ~250 rows).
              The model needs at least 60 clean rows to run; 6 months or more gives reliable accuracy estimates.
              Data is split <strong className="text-foreground">80% train / 20% test</strong> in time order
              — the oldest 80% trains the model, the newest 20% tests it. No shuffling is applied, which
              prevents lookahead bias (a common mistake where future data leaks into training).
            </p>
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium">12 Input Features</div>
            <div className="grid grid-cols-1 gap-1.5">
              {[
                { name: "RSI (14)", desc: "Raw RSI value at each bar." },
                { name: "MACD Histogram", desc: "MACD line minus signal line — positive = bullish momentum." },
                { name: "Bollinger %B", desc: "Where price sits within the bands: 0 = lower band, 1 = upper band." },
                { name: "EMA-9 distance", desc: "(Price − EMA-9) / Price — normalised gap to short-term trend." },
                { name: "EMA-21 distance", desc: "(Price − EMA-21) / Price — normalised gap to medium-term trend." },
                { name: "EMA-50 distance", desc: "(Price − EMA-50) / Price — normalised gap to long-term trend." },
                { name: "EMA-200 distance", desc: "(Price − EMA-200) / Price — normalised gap to very long-term trend." },
                { name: "ATR %", desc: "ATR-14 divided by price — how volatile the stock is relative to its price." },
                { name: "Volume change", desc: "(Today volume / 10-day avg volume) − 1 — unusual volume spikes." },
                { name: "1-day return", desc: "Today's close / yesterday's close − 1 — short-term momentum." },
                { name: "5-day return", desc: "Close vs 5 bars ago / that price − 1 — weekly momentum." },
                { name: "OBV slope", desc: "Linear regression slope of OBV over last 10 bars, normalised by mean OBV." },
              ].map(f => (
                <div key={f.name} className="bg-muted/40 rounded-lg px-3 py-2 flex items-start gap-3">
                  <span className="text-xs font-mono font-semibold text-primary shrink-0 min-w-[130px]">{f.name}</span>
                  <span className="text-xs text-muted-foreground leading-relaxed">{f.desc}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium">Target Variable</div>
            <div className="bg-muted/50 rounded-xl p-4 text-xs text-muted-foreground leading-relaxed">
              Binary: <strong className="text-foreground">1</strong> if the next day's closing price is higher than today's,
              <strong className="text-foreground"> 0</strong> otherwise. The model learns to classify each bar based on
              whether the following day will be an up-day or a down-day.
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium">Prediction & Probability</div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              The trained model is applied to the <strong className="text-foreground">latest bar</strong> (today).
              It outputs a probability of going UP tomorrow. If <strong className="text-foreground">P(UP) ≥ 0.5</strong> the
              direction is UP; otherwise DOWN. The displayed probability is always the confidence in the predicted direction
              (so a DOWN call at 55% means P(DOWN) = 0.55, not P(UP)). Any missing feature values on the latest bar are
              filled with the training-set column means.
            </p>
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium">Accuracy</div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              The accuracy shown is <strong className="text-foreground">test-set accuracy</strong> — the fraction of days
              in the held-out 20% where the model correctly predicted the direction. A random coin flip would score ~50%.
              Typical values on liquid NSE stocks are <strong className="text-foreground">52–58%</strong>.
              This is not a strong edge by itself, but combined with the technical signal score it can confirm or caution against a trade.
            </p>
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 text-xs text-amber-400/90 leading-relaxed">
              <strong>Important:</strong> The model is trained on past data and evaluated on past data. Past accuracy
              does not guarantee future performance. Market conditions change, and the model is retrained fresh
              on each cache miss (roughly hourly). This is a directional indicator, not financial advice.
            </div>
          </div>
        </div>
      </section>

      {/* ── Disclaimer ───────────────────────────────────────────────── */}
      <p className="text-xs text-muted-foreground/60 leading-relaxed border-t border-border pt-6">
        TradeDash is a research and educational tool. All signals, scores, and predictions are generated
        algorithmically from publicly available data. Nothing on this platform constitutes financial advice.
        Always do your own due diligence before making investment decisions.
      </p>
    </div>
  );
}

// ── Local sub-components ──────────────────────────────────────────────────

function SectionHeader({ label, title, sub }: { label: string; title: string; sub: string }) {
  return (
    <div className="flex items-start gap-4">
      <div className="w-8 h-8 rounded-xl bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
        <span className="text-xs font-bold text-primary">{label}</span>
      </div>
      <div>
        <h2 className="text-lg font-bold">{title}</h2>
        <p className="text-muted-foreground text-sm mt-0.5 leading-relaxed">{sub}</p>
      </div>
    </div>
  );
}

function Indicator({
  name,
  period,
  desc,
  rows,
}: {
  name: string;
  period: string;
  desc: string;
  rows: { condition: string; label: string; pts: string }[];
}) {
  return (
    <div className="bg-card border border-border rounded-2xl p-5 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-medium text-sm">{name}</div>
          <div className="text-[11px] text-primary font-mono mt-0.5">{period}</div>
        </div>
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed">{desc}</p>
      <div className="grid grid-cols-1 gap-1">
        {rows.map((r) => {
          const isPos = r.pts.startsWith("+") || (!r.pts.startsWith("−") && r.pts !== "0");
          const isNeg = r.pts.startsWith("−");
          const ptColor = isNeg ? "text-sell" : isPos && r.pts !== "0" ? "text-buy" : "text-muted-foreground";
          return (
            <div key={r.condition} className="flex items-center gap-3 bg-muted/40 rounded-lg px-3 py-1.5">
              <span className="text-xs text-muted-foreground flex-1">{r.condition}</span>
              <span className="text-xs text-muted-foreground/60 text-right hidden sm:block min-w-[140px]">{r.label}</span>
              <span className={`text-xs font-mono font-bold w-10 text-right shrink-0 ${ptColor}`}>{r.pts}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
