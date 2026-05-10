import { KLineStrategyChart } from '../charts/KLineStrategyChart';
import type { Candle, StrategyMarker } from '../charts/types';

const sampleCandles: Candle[] = [
  { timestamp: 1, open: 100, high: 101.2, low: 99.7, close: 100.8, volume: 120000 },
  { timestamp: 2, open: 100.8, high: 102.4, low: 100.6, close: 102.1, volume: 180000 },
  { timestamp: 3, open: 102.1, high: 103.8, low: 101.9, close: 103.5, volume: 240000 },
  { timestamp: 4, open: 103.5, high: 103.9, low: 102.2, close: 102.6, volume: 210000 },
  { timestamp: 5, open: 102.6, high: 104.6, low: 102.5, close: 104.2, volume: 310000 },
];

const sampleMarkers: StrategyMarker[] = [
  { timestamp: 3, price: 103.5, side: 'buy', label: 'Buy breakout' },
  { timestamp: 4, price: 102.2, side: 'exit', label: 'Exit risk' },
];

export function ChartsPage() {
  return <KLineStrategyChart candles={sampleCandles} markers={sampleMarkers} />;
}
