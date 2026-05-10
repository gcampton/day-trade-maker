export type Candle = {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type StrategyMarker = {
  timestamp: number;
  price: number;
  side: 'buy' | 'sell' | 'exit' | 'warning';
  label: string;
};
