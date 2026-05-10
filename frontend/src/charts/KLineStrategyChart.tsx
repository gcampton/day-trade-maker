import type { Candle, StrategyMarker } from './types';

type KLineStrategyChartProps = {
  candles: Candle[];
  markers: StrategyMarker[];
};

export function KLineStrategyChart({ candles, markers }: KLineStrategyChartProps) {
  const high = Math.max(...candles.map((candle) => candle.high));
  const low = Math.min(...candles.map((candle) => candle.low));
  const last = candles.at(-1);

  return (
    <section className="chart-panel" aria-label="KLineCharts strategy chart">
      <div className="chart-panel-header">
        <div>
          <p className="eyebrow">KLineCharts Pro ready</p>
          <h2>Chart Workspace</h2>
          <p>
            Normalized candle and marker props are isolated here so KLineCharts Pro can replace
            this placeholder renderer without changing dashboard data flow.
          </p>
        </div>
        <div className="chart-stat">
          <span>Sample candles</span>
          <strong>{candles.length}</strong>
        </div>
      </div>

      <div className="chart-canvas-placeholder" role="img" aria-label="Sample candlestick chart">
        {candles.map((candle) => {
          const range = Math.max(high - low, 1);
          const top = ((high - candle.high) / range) * 100;
          const height = Math.max(((candle.high - candle.low) / range) * 100, 8);
          const isUp = candle.close >= candle.open;

          return (
            <span
              className={isUp ? 'candle candle-up' : 'candle candle-down'}
              key={candle.timestamp}
              style={{ height: `${height}%`, marginTop: `${top}%` }}
              title={`O ${candle.open} H ${candle.high} L ${candle.low} C ${candle.close}`}
            />
          );
        })}
      </div>

      <dl className="chart-summary">
        <div>
          <dt>Last close</dt>
          <dd>{last?.close.toFixed(2) ?? 'n/a'}</dd>
        </div>
        <div>
          <dt>High</dt>
          <dd>{high.toFixed(2)}</dd>
        </div>
        <div>
          <dt>Low</dt>
          <dd>{low.toFixed(2)}</dd>
        </div>
      </dl>

      <div className="marker-list" aria-label="Strategy markers">
        {markers.map((marker) => (
          <span className={`marker marker-${marker.side}`} key={`${marker.timestamp}-${marker.side}`}>
            {marker.label}
          </span>
        ))}
      </div>
    </section>
  );
}
