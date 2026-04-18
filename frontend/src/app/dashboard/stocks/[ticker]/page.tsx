"use client";
import { useState, useCallback, useMemo } from "react";
import { useParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  CandlestickChart,
  type IndicatorKey,
  type OverlayKey,
  type PanelKey,
} from "@/components/charts/CandlestickChart";
import { ChartControls } from "@/components/charts/ChartControls";
import { IndicatorToggles } from "@/components/charts/IndicatorToggles";
import { IndicatorSubChart } from "@/components/charts/IndicatorSubChart";
import { useChartSync } from "@/components/charts/useChartSync";
import { SignalCard } from "@/components/analysis/SignalCard";
import { IndicatorBreakdown } from "@/components/analysis/IndicatorBreakdown";
import { FundamentalsPanel } from "@/components/analysis/FundamentalsPanel";
import { FundamentalsBreakdown } from "@/components/analysis/FundamentalsBreakdown";
import { MLPredictionCard } from "@/components/analysis/MLPredictionCard";
import { VerdictBanner, classifyVerdict, type Verdict } from "@/components/analysis/VerdictBanner";
import { useSignal, useOHLCV, useCompanyInfo } from "@/lib/api/market";
import { useFundamentals, useMLPredict } from "@/lib/api/analysis";
import { useWebSocketQuote } from "@/lib/api/websocket";
import { INTRADAY, type Interval, type Period } from "@/lib/chartRanges";
import { AlertCircle, RefreshCw, ArrowUp, ArrowDown } from "lucide-react";
import { DataFreshness } from "@/components/ui/DataFreshness";

function ErrorCard({ className }: { className?: string }) {
  return (
    <div
      className={`bg-card border border-border rounded-2xl flex items-center justify-center gap-2 text-muted-foreground text-sm ${className}`}
    >
      <AlertCircle size={14} />
      <span>Data unavailable</span>
    </div>
  );
}

function TickerDashboard({ ticker }: { ticker: string }) {
  const [interval, setInterval] = useState<Interval>("1d");
  const [period, setPeriod] = useState<Period>("max");
  const [indicators, setIndicators] = useState<IndicatorKey[]>([]);
  const registerChart = useChartSync();
  const onMainChartReady = useCallback(
    (chart: Parameters<typeof registerChart>[1], series: Parameters<typeof registerChart>[2]) =>
      registerChart("main", chart, series),
    [registerChart],
  );
  const panelCallbacks = useMemo(
    () =>
      Object.fromEntries(
        (["rsi", "macd", "obv"] as const).map((pk) => [
          pk,
          (chart: Parameters<typeof registerChart>[1], series: Parameters<typeof registerChart>[2]) =>
            registerChart(pk, chart, series),
        ]),
      ) as Record<
        PanelKey,
        (chart: Parameters<typeof registerChart>[1], series: Parameters<typeof registerChart>[2]) => ReturnType<typeof registerChart>
      >,
    [registerChart],
  );

  const toggleIndicator = (key: IndicatorKey) =>
    setIndicators((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key],
    );

  const PANEL_KEYS: PanelKey[] = ["rsi", "macd", "obv"];
  const overlayKeys = indicators.filter(
    (k): k is OverlayKey => !PANEL_KEYS.includes(k as PanelKey),
  );
  const panelKeys = indicators.filter((k): k is PanelKey =>
    PANEL_KEYS.includes(k as PanelKey),
  );

  const signalPeriod: Period = INTRADAY.has(interval) ? period : "6mo";
  const signalInterval: Interval = INTRADAY.has(interval) ? interval : "1d";

  const { data: signal, isLoading: signalLoading, isError: signalError, isFetching: signalFetching, dataUpdatedAt: signalUpdatedAt } =
    useSignal(ticker, signalInterval, signalPeriod);
  const { data: ohlcv, isLoading: ohlcvLoading, isError: ohlcvError } = useOHLCV(
    ticker,
    interval,
    period,
    indicators.length > 0,
  );
  const { data: companyInfo } = useCompanyInfo(ticker);
  const { data: fundamentals, isLoading: fundsLoading, isFetching: fundsFetching } = useFundamentals(ticker);
  const { data: ml, isLoading: mlLoading, isFetching: mlFetching } = useMLPredict(ticker);

  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("technical");
  const refreshTab = useCallback(() => {
    if (activeTab === "technical") {
      queryClient.invalidateQueries({ queryKey: ["signal", ticker] });
    } else if (activeTab === "fundamental") {
      queryClient.invalidateQueries({ queryKey: ["fundamentals", ticker] });
    } else if (activeTab === "ml") {
      queryClient.invalidateQueries({ queryKey: ["ml-predict", ticker] });
    }
  }, [activeTab, ticker, queryClient]);

  const isRefreshing =
    (activeTab === "technical" && signalFetching) ||
    (activeTab === "fundamental" && fundsFetching) ||
    (activeTab === "ml" && mlFetching);

  const fundsName = fundamentals?.fundamentals?.name
    ? String(fundamentals.fundamentals.name)
    : null;
  const displayName =
    companyInfo?.name && companyInfo.name !== ticker
      ? companyInfo.name
      : fundsName ?? ticker.replace(/\.(NS|BO)$/i, "");

  const wsQuote = useWebSocketQuote(ticker);
  // WS price takes precedence over the cached signal price once connected
  const livePrice = wsQuote?.price ?? signal?.last_price ?? null;
  const priceLabel = signalLoading
    ? null
    : livePrice
    ? `₹${livePrice.toFixed(2)}`
    : signalError
    ? "Unavailable"
    : "—";

  const techVerdict: Verdict = classifyVerdict(signal?.confidence);
  const techHeadline = signal
    ? `${signal.signal} · ${signal.confidence}% confidence`
    : "Awaiting signal";
  const techSub = signal
    ? `Entry ₹${signal.last_price.toFixed(2)} · SL ₹${signal.stop_loss.toFixed(
        2,
      )} · Target ₹${signal.target.toFixed(2)}`
    : undefined;

  const fundVerdict: Verdict = classifyVerdict(fundamentals?.score);
  const fundHeadline = fundamentals?.grade
    ? `${fundamentals.grade} fundamentals`
    : "Fundamental data";
  const fundSub = fundamentals?.fundamentals?.sector
    ? String(fundamentals.fundamentals.sector)
    : undefined;

  const mlDirection = ml?.direction;
  const mlVerdict: Verdict =
    mlDirection === "UP" ? "BULLISH" : mlDirection === "DOWN" ? "BEARISH" : "NEUTRAL";
  const mlProb = ml?.probability != null ? Math.round(ml.probability * 100) : null;
  const mlHeadline = mlDirection
    ? `Next day: ${mlDirection}${mlProb != null ? ` · ${mlProb}% probability` : ""}`
    : "Model unavailable";
  const mlSub =
    ml?.accuracy != null ? `Model accuracy ${Math.round(ml.accuracy * 100)}%` : undefined;

  const high52w = fundamentals?.fundamentals?.high_52w as number | null | undefined;
  const low52w = fundamentals?.fundamentals?.low_52w as number | null | undefined;

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold">{displayName}</h1>
          <span className="flex items-center gap-2 flex-wrap text-muted-foreground text-sm mt-0.5">
            <span className="text-muted-foreground/50">{ticker}</span>
            {priceLabel ?? <Skeleton className="w-24 h-4 inline-block" />}
            <DataFreshness updatedAt={signalUpdatedAt} />
          </span>
        </div>
        <div>
          {signalLoading ? (
            <Skeleton className="w-16 h-7 rounded-full" />
          ) : signal ? (
            <div
              className={`text-sm font-bold px-4 py-1.5 rounded-full ${
                signal.signal === "BUY"
                  ? "bg-buy/10 text-buy"
                  : signal.signal === "SELL"
                  ? "bg-sell/10 text-sell"
                  : "bg-hold/10 text-hold"
              }`}
            >
              {signal.signal}
            </div>
          ) : (
            <div className="text-sm font-bold px-4 py-1.5 rounded-full bg-muted text-muted-foreground">
              —
            </div>
          )}
        </div>
      </div>

      {/* 52-Week Range */}
      {high52w != null && low52w != null && signal?.last_price != null && (
        <div className="bg-card border border-border rounded-2xl px-4 py-3 flex items-center gap-3 min-w-0">
          <div className="flex items-center gap-1.5 text-sm">
            <ArrowDown size={13} className="text-sell" />
            <span className="text-muted-foreground text-xs">52W Low</span>
            <span className="font-mono font-semibold tabular-nums">₹{low52w.toFixed(2)}</span>
          </div>
          <div className="flex-1 relative h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="absolute inset-y-0 left-0 bg-gradient-to-r from-sell/60 via-hold/60 to-buy/60 rounded-full"
              style={{ width: "100%" }}
            />
            {(() => {
              const pct = Math.min(100, Math.max(0, ((signal.last_price - low52w) / (high52w - low52w)) * 100));
              return (
                <div
                  className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-foreground rounded-full border-2 border-card shadow"
                  style={{ left: `${pct}%` }}
                />
              );
            })()}
          </div>
          <div className="flex items-center gap-1.5 text-sm">
            <ArrowUp size={13} className="text-buy" />
            <span className="text-muted-foreground text-xs">52W High</span>
            <span className="font-mono font-semibold tabular-nums">₹{high52w.toFixed(2)}</span>
          </div>
        </div>
      )}

      {/* Chart + controls */}
      <div className="bg-card border border-border rounded-2xl p-4">
        <div className="flex items-center justify-between gap-2 mb-3">
          <p className="text-xs text-muted-foreground">
            {ohlcv?.candles ? `${ohlcv.candles.length} candles` : ""}
          </p>
          <ChartControls
            interval={interval}
            period={period}
            onChange={({ interval: i, period: p }) => {
              setInterval(i);
              setPeriod(p);
            }}
          />
        </div>
        <div className="mb-3">
          <IndicatorToggles selected={indicators} onToggle={toggleIndicator} />
        </div>
        {ohlcvLoading ? (
          <Skeleton className="w-full h-90 rounded-xl" />
        ) : ohlcv && ohlcv.candles.length > 0 ? (
          <>
            <CandlestickChart
              candles={ohlcv.candles}
              height={360}
              intraday={INTRADAY.has(interval)}
              indicators={overlayKeys}
              onChartReady={onMainChartReady}
            />
            {panelKeys.map((pk) => (
              <IndicatorSubChart
                key={pk}
                kind={pk}
                candles={ohlcv.candles}
                height={140}
                intraday={INTRADAY.has(interval)}
                onChartReady={panelCallbacks[pk]}
              />
            ))}
          </>
        ) : (
          <div className="h-90 flex flex-col items-center justify-center gap-2 text-muted-foreground text-sm">
            <AlertCircle size={20} className="opacity-40" />
            <span>{ohlcvError ? "Chart unavailable" : "No data"}</span>
          </div>
        )}
      </div>

      {/* Analysis tabs */}
      <Tabs defaultValue="technical" className="flex-col" onValueChange={setActiveTab}>
        <div className="flex items-center justify-between">
          <TabsList className="bg-muted/50 rounded-xl w-fit">
            <TabsTrigger value="technical" className="rounded-lg">Technical</TabsTrigger>
            <TabsTrigger value="fundamental" className="rounded-lg">Fundamental</TabsTrigger>
            <TabsTrigger value="ml" className="rounded-lg">ML Prediction</TabsTrigger>
          </TabsList>
          <button
            onClick={refreshTab}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors px-3 py-1.5 rounded-lg hover:bg-muted/50 disabled:opacity-50"
          >
            <RefreshCw size={13} className={isRefreshing ? "animate-spin" : ""} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Technical */}
        <TabsContent value="technical" className="mt-4 space-y-4">
          {signalLoading ? (
            <>
              <Skeleton className="h-20 rounded-2xl" />
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <Skeleton className="h-48 rounded-2xl" />
                <Skeleton className="h-48 rounded-2xl" />
              </div>
            </>
          ) : signal ? (
            <>
              <VerdictBanner
                verdict={techVerdict}
                headline={techHeadline}
                sublabel={techSub}
                score={signal.confidence}
              />
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <SignalCard data={signal} />
                <IndicatorBreakdown components={signal.components} />
              </div>
            </>
          ) : (
            <ErrorCard className="h-32" />
          )}
        </TabsContent>

        {/* Fundamental */}
        <TabsContent value="fundamental" className="mt-4 space-y-4">
          {fundsLoading ? (
            <>
              <Skeleton className="h-20 rounded-2xl" />
              <Skeleton className="h-64 rounded-2xl" />
            </>
          ) : fundamentals ? (
            <>
              <VerdictBanner
                verdict={fundVerdict}
                headline={fundHeadline}
                sublabel={fundSub}
                score={fundamentals.score}
              />
              <FundamentalsPanel
                data={fundamentals.fundamentals}
                ticker={ticker}
              />
              {fundamentals.breakdown && (
                <FundamentalsBreakdown breakdown={fundamentals.breakdown} />
              )}
            </>
          ) : (
            <ErrorCard className="h-32" />
          )}
        </TabsContent>

        {/* ML Prediction */}
        <TabsContent value="ml" className="mt-4 space-y-4">
          {mlLoading ? (
            <>
              <Skeleton className="h-20 rounded-2xl" />
              <Skeleton className="h-48 rounded-2xl" />
            </>
          ) : ml ? (
            <>
              <VerdictBanner
                verdict={mlVerdict}
                headline={mlHeadline}
                sublabel={mlSub}
                score={mlProb ?? undefined}
              />
              <MLPredictionCard data={ml} />
            </>
          ) : (
            <ErrorCard className="h-32" />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default function TickerPage() {
  const params = useParams();
  const ticker = Array.isArray(params.ticker)
    ? params.ticker[0]
    : (params.ticker as string);
  return <TickerDashboard ticker={ticker} />;
}
