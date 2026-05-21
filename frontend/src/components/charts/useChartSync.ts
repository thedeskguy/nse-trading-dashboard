import { useRef, useCallback } from "react";
import type { IChartApi, ISeriesApi, SeriesType, LogicalRange, MouseEventParams } from "lightweight-charts";

type ChartEntry = {
  chart: IChartApi;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  series: ISeriesApi<SeriesType, any> | null;
};

export function useChartSync() {
  const chartsRef = useRef<Map<string, ChartEntry>>(new Map());
  const syncingRef = useRef(false);

  const register = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (id: string, chart: IChartApi, series?: ISeriesApi<SeriesType, any>) => {
      chartsRef.current.set(id, { chart, series: series ?? null });

      chart.timeScale().subscribeVisibleLogicalRangeChange((range: LogicalRange | null) => {
        if (syncingRef.current || !range) return;
        syncingRef.current = true;
        chartsRef.current.forEach((entry, otherId) => {
          if (otherId !== id) {
            entry.chart.timeScale().setVisibleLogicalRange(range);
          }
        });
        syncingRef.current = false;
      });

      chart.subscribeCrosshairMove((param: MouseEventParams) => {
        if (syncingRef.current) return;
        syncingRef.current = true;
        chartsRef.current.forEach((entry, otherId) => {
          if (otherId !== id && entry.series) {
            if (param.time) {
              entry.chart.setCrosshairPosition(NaN, param.time, entry.series);
            } else {
              entry.chart.clearCrosshairPosition();
            }
          }
        });
        syncingRef.current = false;
      });

      return () => {
        chartsRef.current.delete(id);
      };
    },
    [],
  );

  return register;
}
