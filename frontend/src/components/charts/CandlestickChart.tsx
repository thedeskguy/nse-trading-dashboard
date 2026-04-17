"use client";
import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  CrosshairMode,
  CandlestickSeries,
  LineSeries,
} from "lightweight-charts";
import type { Candle } from "@/lib/api/market";

export type OverlayKey =
  | "ema_9"
  | "ema_21"
  | "ema_50"
  | "ema_200"
  | "bb_upper"
  | "bb_middle"
  | "bb_lower";

export type PanelKey = "rsi" | "macd" | "obv";

export type IndicatorKey = OverlayKey | PanelKey;

export const INDICATOR_META: Record<
  IndicatorKey,
  { label: string; color: string; group: "ema" | "bb" | "panel" }
> = {
  ema_9:     { label: "EMA 9",    color: "#FFD60A", group: "ema" },
  ema_21:    { label: "EMA 21",   color: "#FF9F0A", group: "ema" },
  ema_50:    { label: "EMA 50",   color: "#0A84FF", group: "ema" },
  ema_200:   { label: "EMA 200",  color: "#BF5AF2", group: "ema" },
  bb_upper:  { label: "BB Upper", color: "#64D2FF", group: "bb" },
  bb_middle: { label: "BB Mid",   color: "#8E8E93", group: "bb" },
  bb_lower:  { label: "BB Lower", color: "#64D2FF", group: "bb" },
  rsi:       { label: "RSI",      color: "#7B61FF", group: "panel" },
  macd:      { label: "MACD",     color: "#0A84FF", group: "panel" },
  obv:       { label: "OBV",      color: "#BF5AF2", group: "panel" },
};

import type { IChartApi, ISeriesApi, SeriesType } from "lightweight-charts";

interface Props {
  candles: Candle[];
  height?: number;
  intraday?: boolean;
  indicators?: OverlayKey[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onChartReady?: (chart: IChartApi, series: ISeriesApi<SeriesType, any>) => (() => void) | void;
}

export function CandlestickChart({
  candles,
  height = 360,
  intraday = false,
  indicators = [],
  onChartReady,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || candles.length === 0) return;

    const w = containerRef.current.getBoundingClientRect().width || 800;

    const chart = createChart(containerRef.current, {
      width: w,
      height,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "rgba(255,255,255,0.5)",
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)" },
        horzLines: { color: "rgba(255,255,255,0.04)" },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.1)" },
      timeScale: { borderColor: "rgba(255,255,255,0.1)", timeVisible: true },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#30D158",
      downColor: "#FF453A",
      borderUpColor: "#30D158",
      borderDownColor: "#FF453A",
      wickUpColor: "#30D158",
      wickDownColor: "#FF453A",
    });

    const toTime = (ts: string): number | string =>
      intraday
        ? (Math.floor(new Date(ts).getTime() / 1000) as number)
        : (ts.split("T")[0] as string);

    const seen = new Set<number | string>();
    const rows = candles
      .map((c) => ({ c, time: toTime(c.timestamp) }))
      .filter(({ time }) => {
        if (seen.has(time)) return false;
        seen.add(time);
        return true;
      })
      .sort((a, b) => (a.time < b.time ? -1 : 1));

    if (rows.length === 0) return;

    const candleData = rows.map(({ c, time }) => ({
      time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));

    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      candleSeries.setData(candleData as any);

      for (const key of indicators) {
        const meta = INDICATOR_META[key];
        if (!meta) continue;
        const lineData = rows
          .map(({ c, time }) => {
            const v = c[key];
            return v == null ? null : { time, value: v };
          })
          .filter((p): p is { time: number | string; value: number } => p !== null);
        if (lineData.length === 0) continue;
        const line = chart.addSeries(LineSeries, {
          color: meta.color,
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        line.setData(lineData as any);
      }

      chart.timeScale().fitContent();
    } catch {
      // malformed data — chart stays empty rather than crashing
    }

    const syncCleanup = onChartReady?.(chart, candleSeries);

    const ro = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (rect && rect.width > 0) {
        chart.applyOptions({ width: rect.width });
      }
    });
    ro.observe(containerRef.current);

    return () => {
      syncCleanup?.();
      ro.disconnect();
      chart.remove();
    };
  }, [candles, height, intraday, indicators, onChartReady]);

  return <div ref={containerRef} style={{ height }} className="w-full" />;
}
