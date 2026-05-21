"use client";
import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  CrosshairMode,
  LineSeries,
  HistogramSeries,
  AreaSeries,
} from "lightweight-charts";
import type { IChartApi, ISeriesApi, SeriesType } from "lightweight-charts";
import type { Candle } from "@/lib/api/market";

type PanelKind = "rsi" | "macd" | "obv";

interface Props {
  kind: PanelKind;
  candles: Candle[];
  height?: number;
  intraday?: boolean;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onChartReady?: (chart: IChartApi, series: ISeriesApi<SeriesType, any>) => (() => void) | void;
}

const PANEL_CONFIG: Record<
  PanelKind,
  { label: string; series: { key: keyof Candle; color: string; type: "line" | "histogram" }[] }
> = {
  rsi: {
    label: "RSI (14)",
    series: [{ key: "rsi_14", color: "#7B61FF", type: "line" }],
  },
  macd: {
    label: "MACD",
    series: [
      { key: "macd", color: "#0A84FF", type: "line" },
      { key: "macd_signal", color: "#FF453A", type: "line" },
      { key: "macd_hist", color: "#30D158", type: "histogram" },
    ],
  },
  obv: {
    label: "OBV",
    series: [{ key: "obv", color: "#BF5AF2", type: "line" }],
  },
};

export function IndicatorSubChart({ kind, candles, height = 140, intraday = false, onChartReady }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const config = PANEL_CONFIG[kind];

  useEffect(() => {
    if (!containerRef.current || candles.length === 0) return;

    const w = containerRef.current.getBoundingClientRect().width || 800;

    const isRSI = kind === "rsi";

    const chart = createChart(containerRef.current, {
      width: w,
      height,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "rgba(255,255,255,0.5)",
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)" },
        horzLines: { color: isRSI ? "rgba(255,255,255,0.02)" : "rgba(255,255,255,0.04)" },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: {
        borderColor: "rgba(255,255,255,0.1)",
        ...(isRSI ? { autoScale: false, scaleMargins: { top: 0.02, bottom: 0.02 } } : {}),
      },
      timeScale: { borderColor: "rgba(255,255,255,0.1)", timeVisible: true },
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

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let primarySeries: ISeriesApi<SeriesType, any> | null = null;

    try {
      const times = rows.map(({ time }) => time);

      if (isRSI) {
        const oversoldBand = chart.addSeries(AreaSeries, {
          topColor: "rgba(46, 204, 113, 0.08)",
          bottomColor: "rgba(46, 204, 113, 0.02)",
          lineColor: "rgba(46, 204, 113, 0.3)",
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        oversoldBand.setData(times.map((t) => ({ time: t, value: 30 })) as any);

        const overboughtBand = chart.addSeries(AreaSeries, {
          topColor: "rgba(231, 76, 60, 0.08)",
          bottomColor: "rgba(231, 76, 60, 0.02)",
          lineColor: "rgba(231, 76, 60, 0.3)",
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        overboughtBand.setData(times.map((t) => ({ time: t, value: 70 })) as any);
      }

      for (const s of config.series) {
        const points = rows
          .map(({ c, time }) => {
            const v = c[s.key] as number | null | undefined;
            return v == null ? null : { time, value: v };
          })
          .filter((p): p is { time: number | string; value: number } => p !== null);
        if (points.length === 0) continue;

        if (s.type === "histogram") {
          const hist = chart.addSeries(HistogramSeries, {
            color: s.color,
            priceLineVisible: false,
            lastValueVisible: false,
          });
          const histData = points.map((p) => ({
            ...p,
            color: p.value >= 0 ? "#30D158" : "#FF453A",
          }));
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          hist.setData(histData as any);
          if (!primarySeries) primarySeries = hist;
        } else {
          const line = chart.addSeries(LineSeries, {
            color: s.color,
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: false,
          });
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          line.setData(points as any);
          if (!primarySeries) primarySeries = line;

          if (isRSI) {
            line.createPriceLine({
              price: 70,
              color: "rgba(231, 76, 60, 0.5)",
              lineWidth: 1,
              lineStyle: 2,
              axisLabelVisible: true,
              title: "",
            });
            line.createPriceLine({
              price: 50,
              color: "rgba(255, 255, 255, 0.15)",
              lineWidth: 1,
              lineStyle: 2,
              axisLabelVisible: false,
              title: "",
            });
            line.createPriceLine({
              price: 30,
              color: "rgba(46, 204, 113, 0.5)",
              lineWidth: 1,
              lineStyle: 2,
              axisLabelVisible: true,
              title: "",
            });
          }
        }
      }
      chart.timeScale().fitContent();
    } catch {
      // malformed data
    }

    const syncCleanup = primarySeries ? onChartReady?.(chart, primarySeries) : undefined;

    const ro = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (rect && rect.width > 0) chart.applyOptions({ width: rect.width });
    });
    ro.observe(containerRef.current);

    return () => {
      syncCleanup?.();
      ro.disconnect();
      chart.remove();
    };
  }, [kind, candles, height, intraday, config, onChartReady]);

  return (
    <div>
      <p className="text-xs text-muted-foreground mb-1 font-medium">{config.label}</p>
      <div ref={containerRef} style={{ height }} className="w-full" />
    </div>
  );
}
