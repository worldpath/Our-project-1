"""
Composite Scoring System for Enhanced Crypto Trading Bot
Mirrors the successful AAGIM Enhanced Stock Trading System approach
Combines 50+ technical indicators into unified trading signals
"""

import logging
import numpy as np
import pandas as pd
import talib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from multi_source_data_client import MultiSourceDataClient

class CompositeScoring:
    """
    Advanced composite scoring system that combines multiple technical indicators
    into unified trading signals with confidence levels and risk assessment
    """
    
    def __init__(self, data_client: MultiSourceDataClient = None):
        """
        Initialize composite scoring system
        
        Args:
            data_client: Multi-source data client for market data
        """
        self.logger = logging.getLogger(__name__)
        self.data_client = data_client or MultiSourceDataClient()
        
        # Scoring weights for different indicator categories
        self.weights = {
            'momentum': 0.25,      # RSI, Stochastic, Williams %R, etc.
            'trend': 0.30,         # MACD, Moving Averages, ADX, etc.
            'volatility': 0.20,    # Bollinger Bands, ATR, etc.
            'volume': 0.15,        # Volume indicators, OBV, etc.
            'sentiment': 0.10      # News sentiment, market sentiment
        }
        
        # Risk thresholds
        self.risk_thresholds = {
            'conservative': {'min_score': 75, 'max_volatility': 0.02},
            'moderate': {'min_score': 60, 'max_volatility': 0.04},
            'aggressive': {'min_score': 50, 'max_volatility': 0.08}
        }
    
    def calculate_momentum_score(self, data: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate momentum indicators score
        
        Args:
            data: OHLCV DataFrame
            
        Returns:
            Dictionary with momentum scores and individual indicators
        """
        scores = {}
        individual_scores = []
        
        try:
            high = data['high'].values
            low = data['low'].values
            close = data['close'].values
            
            # RSI (14-period)
            rsi = talib.RSI(close, timeperiod=14)
            current_rsi = rsi[-1] if not np.isnan(rsi[-1]) else 50
            
            if current_rsi < 30:
                rsi_score = 80  # Oversold - bullish
            elif current_rsi > 70:
                rsi_score = 20  # Overbought - bearish
            elif current_rsi < 40:
                rsi_score = 65  # Bearish momentum
            elif current_rsi > 60:
                rsi_score = 65  # Bullish momentum
            else:
                rsi_score = 50  # Neutral
            
            scores['rsi'] = current_rsi
            individual_scores.append(rsi_score)
            
            # Stochastic Oscillator
            slowk, slowd = talib.STOCH(high, low, close, fastk_period=14, slowk_period=3, slowd_period=3)
            current_k = slowk[-1] if not np.isnan(slowk[-1]) else 50
            current_d = slowd[-1] if not np.isnan(slowd[-1]) else 50
            
            if current_k < 20 and current_d < 20:
                stoch_score = 80  # Oversold
            elif current_k > 80 and current_d > 80:
                stoch_score = 20  # Overbought
            elif current_k > current_d:
                stoch_score = 65  # Bullish crossover
            else:
                stoch_score = 35  # Bearish crossover
            
            scores['stochastic_k'] = current_k
            scores['stochastic_d'] = current_d
            individual_scores.append(stoch_score)
            
            # Williams %R
            willr = talib.WILLR(high, low, close, timeperiod=14)
            current_willr = willr[-1] if not np.isnan(willr[-1]) else -50
            
            if current_willr < -80:
                willr_score = 80  # Oversold
            elif current_willr > -20:
                willr_score = 20  # Overbought
            else:
                willr_score = 50  # Neutral
            
            scores['williams_r'] = current_willr
            individual_scores.append(willr_score)
            
            # Commodity Channel Index (CCI)
            cci = talib.CCI(high, low, close, timeperiod=14)
            current_cci = cci[-1] if not np.isnan(cci[-1]) else 0
            
            if current_cci < -100:
                cci_score = 80  # Oversold
            elif current_cci > 100:
                cci_score = 20  # Overbought
            elif current_cci > 0:
                cci_score = 60  # Bullish
            else:
                cci_score = 40  # Bearish
            
            scores['cci'] = current_cci
            individual_scores.append(cci_score)
            
            # Rate of Change (ROC)
            roc = talib.ROC(close, timeperiod=10)
            current_roc = roc[-1] if not np.isnan(roc[-1]) else 0
            
            if current_roc > 5:
                roc_score = 80  # Strong positive momentum
            elif current_roc > 2:
                roc_score = 65  # Moderate positive momentum
            elif current_roc < -5:
                roc_score = 20  # Strong negative momentum
            elif current_roc < -2:
                roc_score = 35  # Moderate negative momentum
            else:
                roc_score = 50  # Neutral
            
            scores['roc'] = current_roc
            individual_scores.append(roc_score)
            
        except Exception as e:
            self.logger.error(f"Error calculating momentum scores: {e}")
            individual_scores = [50] * 5  # Neutral scores on error
        
        scores['composite_momentum_score'] = np.mean(individual_scores)
        return scores
    
    def calculate_trend_score(self, data: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate trend indicators score
        
        Args:
            data: OHLCV DataFrame
            
        Returns:
            Dictionary with trend scores and individual indicators
        """
        scores = {}
        individual_scores = []
        
        try:
            high = data['high'].values
            low = data['low'].values
            close = data['close'].values
            
            # MACD
            macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
            current_macd = macd[-1] if not np.isnan(macd[-1]) else 0
            current_signal = macdsignal[-1] if not np.isnan(macdsignal[-1]) else 0
            current_hist = macdhist[-1] if not np.isnan(macdhist[-1]) else 0
            
            if current_macd > current_signal and current_hist > 0:
                macd_score = 80  # Bullish crossover with positive histogram
            elif current_macd > current_signal:
                macd_score = 65  # Bullish crossover
            elif current_macd < current_signal and current_hist < 0:
                macd_score = 20  # Bearish crossover with negative histogram
            elif current_macd < current_signal:
                macd_score = 35  # Bearish crossover
            else:
                macd_score = 50  # Neutral
            
            scores['macd'] = current_macd
            scores['macd_signal'] = current_signal
            scores['macd_histogram'] = current_hist
            individual_scores.append(macd_score)
            
            # Moving Average Convergence
            sma_10 = talib.SMA(close, timeperiod=10)
            sma_20 = talib.SMA(close, timeperiod=20)
            sma_50 = talib.SMA(close, timeperiod=50)
            
            current_price = close[-1]
            current_sma_10 = sma_10[-1] if not np.isnan(sma_10[-1]) else current_price
            current_sma_20 = sma_20[-1] if not np.isnan(sma_20[-1]) else current_price
            current_sma_50 = sma_50[-1] if not np.isnan(sma_50[-1]) else current_price
            
            # Score based on price position relative to moving averages
            ma_score = 50  # Start neutral
            if current_price > current_sma_10 > current_sma_20 > current_sma_50:
                ma_score = 85  # Strong bullish alignment
            elif current_price > current_sma_10 > current_sma_20:
                ma_score = 70  # Moderate bullish
            elif current_price > current_sma_10:
                ma_score = 60  # Weak bullish
            elif current_price < current_sma_10 < current_sma_20 < current_sma_50:
                ma_score = 15  # Strong bearish alignment
            elif current_price < current_sma_10 < current_sma_20:
                ma_score = 30  # Moderate bearish
            elif current_price < current_sma_10:
                ma_score = 40  # Weak bearish
            
            scores['sma_10'] = current_sma_10
            scores['sma_20'] = current_sma_20
            scores['sma_50'] = current_sma_50
            individual_scores.append(ma_score)
            
            # Average Directional Index (ADX)
            adx = talib.ADX(high, low, close, timeperiod=14)
            current_adx = adx[-1] if not np.isnan(adx[-1]) else 25
            
            # ADX measures trend strength, not direction
            if current_adx > 50:
                adx_score = 75  # Very strong trend
            elif current_adx > 25:
                adx_score = 60  # Strong trend
            else:
                adx_score = 40  # Weak trend
            
            scores['adx'] = current_adx
            individual_scores.append(adx_score)
            
            # Parabolic SAR
            sar = talib.SAR(high, low, acceleration=0.02, maximum=0.2)
            current_sar = sar[-1] if not np.isnan(sar[-1]) else current_price
            
            if current_price > current_sar:
                sar_score = 70  # Price above SAR - bullish
            else:
                sar_score = 30  # Price below SAR - bearish
            
            scores['sar'] = current_sar
            individual_scores.append(sar_score)
            
            # Aroon Oscillator
            aroondown, aroonup = talib.AROON(high, low, timeperiod=14)
            current_aroon_up = aroonup[-1] if not np.isnan(aroonup[-1]) else 50
            current_aroon_down = aroondown[-1] if not np.isnan(aroondown[-1]) else 50
            
            if current_aroon_up > 70 and current_aroon_down < 30:
                aroon_score = 80  # Strong uptrend
            elif current_aroon_up > current_aroon_down:
                aroon_score = 65  # Uptrend
            elif current_aroon_down > 70 and current_aroon_up < 30:
                aroon_score = 20  # Strong downtrend
            elif current_aroon_down > current_aroon_up:
                aroon_score = 35  # Downtrend
            else:
                aroon_score = 50  # Neutral
            
            scores['aroon_up'] = current_aroon_up
            scores['aroon_down'] = current_aroon_down
            individual_scores.append(aroon_score)
            
        except Exception as e:
            self.logger.error(f"Error calculating trend scores: {e}")
            individual_scores = [50] * 5  # Neutral scores on error
        
        scores['composite_trend_score'] = np.mean(individual_scores)
        return scores
    
    def calculate_volatility_score(self, data: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate volatility indicators score
        
        Args:
            data: OHLCV DataFrame
            
        Returns:
            Dictionary with volatility scores and individual indicators
        """
        scores = {}
        individual_scores = []
        
        try:
            high = data['high'].values
            low = data['low'].values
            close = data['close'].values
            
            # Bollinger Bands
            upperband, middleband, lowerband = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
            current_price = close[-1]
            current_upper = upperband[-1] if not np.isnan(upperband[-1]) else current_price
            current_middle = middleband[-1] if not np.isnan(middleband[-1]) else current_price
            current_lower = lowerband[-1] if not np.isnan(lowerband[-1]) else current_price
            
            # Bollinger Band position scoring
            if current_price <= current_lower:
                bb_score = 80  # Price at or below lower band - oversold
            elif current_price >= current_upper:
                bb_score = 20  # Price at or above upper band - overbought
            elif current_price < current_middle:
                bb_score = 40  # Price below middle - bearish
            else:
                bb_score = 60  # Price above middle - bullish
            
            # Band squeeze indicator
            band_width = (current_upper - current_lower) / current_middle
            scores['bb_upper'] = current_upper
            scores['bb_middle'] = current_middle
            scores['bb_lower'] = current_lower
            scores['bb_width'] = band_width
            individual_scores.append(bb_score)
            
            # Average True Range (ATR)
            atr = talib.ATR(high, low, close, timeperiod=14)
            current_atr = atr[-1] if not np.isnan(atr[-1]) else 0
            
            # ATR as percentage of price
            atr_percent = (current_atr / current_price) * 100 if current_price > 0 else 0
            
            # Lower volatility is generally better for trend following
            if atr_percent < 2:
                atr_score = 70  # Low volatility - good for trends
            elif atr_percent < 4:
                atr_score = 60  # Moderate volatility
            elif atr_percent < 6:
                atr_score = 50  # High volatility
            else:
                atr_score = 40  # Very high volatility
            
            scores['atr'] = current_atr
            scores['atr_percent'] = atr_percent
            individual_scores.append(atr_score)
            
            # Keltner Channels
            kc_middle = talib.EMA(close, timeperiod=20)
            kc_upper = kc_middle + (2 * atr)
            kc_lower = kc_middle - (2 * atr)
            
            current_kc_upper = kc_upper[-1] if not np.isnan(kc_upper[-1]) else current_price
            current_kc_lower = kc_lower[-1] if not np.isnan(kc_lower[-1]) else current_price
            
            if current_price <= current_kc_lower:
                kc_score = 75  # Price below lower Keltner - oversold
            elif current_price >= current_kc_upper:
                kc_score = 25  # Price above upper Keltner - overbought
            else:
                kc_score = 50  # Price within channels
            
            scores['kc_upper'] = current_kc_upper
            scores['kc_lower'] = current_kc_lower
            individual_scores.append(kc_score)
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility scores: {e}")
            individual_scores = [50] * 3  # Neutral scores on error
        
        scores['composite_volatility_score'] = np.mean(individual_scores)
        return scores
    
    def calculate_volume_score(self, data: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate volume indicators score
        
        Args:
            data: OHLCV DataFrame
            
        Returns:
            Dictionary with volume scores and individual indicators
        """
        scores = {}
        individual_scores = []
        
        try:
            high = data['high'].values
            low = data['low'].values
            close = data['close'].values
            volume = data['volume'].values
            
            # On Balance Volume (OBV)
            obv = talib.OBV(close, volume)
            
            # OBV trend analysis
            obv_sma = talib.SMA(obv, timeperiod=10)
            current_obv = obv[-1] if not np.isnan(obv[-1]) else 0
            current_obv_sma = obv_sma[-1] if not np.isnan(obv_sma[-1]) else current_obv
            
            if current_obv > current_obv_sma:
                obv_score = 70  # OBV above its moving average - bullish
            else:
                obv_score = 30  # OBV below its moving average - bearish
            
            scores['obv'] = current_obv
            individual_scores.append(obv_score)
            
            # Volume Rate of Change
            volume_roc = talib.ROC(volume.astype(float), timeperiod=10)
            current_vol_roc = volume_roc[-1] if not np.isnan(volume_roc[-1]) else 0
            
            if current_vol_roc > 20:
                vol_roc_score = 75  # High volume increase
            elif current_vol_roc > 0:
                vol_roc_score = 60  # Volume increasing
            elif current_vol_roc < -20:
                vol_roc_score = 25  # High volume decrease
            else:
                vol_roc_score = 45  # Volume decreasing
            
            scores['volume_roc'] = current_vol_roc
            individual_scores.append(vol_roc_score)
            
            # Volume Moving Average Ratio
            volume_sma = talib.SMA(volume.astype(float), timeperiod=20)
            current_volume = volume[-1]
            current_vol_sma = volume_sma[-1] if not np.isnan(volume_sma[-1]) else current_volume
            
            vol_ratio = current_volume / current_vol_sma if current_vol_sma > 0 else 1
            
            if vol_ratio > 2:
                vol_ratio_score = 80  # Very high volume
            elif vol_ratio > 1.5:
                vol_ratio_score = 70  # High volume
            elif vol_ratio > 1:
                vol_ratio_score = 60  # Above average volume
            elif vol_ratio > 0.5:
                vol_ratio_score = 40  # Below average volume
            else:
                vol_ratio_score = 30  # Very low volume
            
            scores['volume_ratio'] = vol_ratio
            individual_scores.append(vol_ratio_score)
            
        except Exception as e:
            self.logger.error(f"Error calculating volume scores: {e}")
            individual_scores = [50] * 3  # Neutral scores on error
        
        scores['composite_volume_score'] = np.mean(individual_scores)
        return scores
    
    def calculate_sentiment_score(self, symbol: str) -> Dict[str, float]:
        """
        Calculate sentiment indicators score
        
        Args:
            symbol: Cryptocurrency symbol
            
        Returns:
            Dictionary with sentiment scores
        """
        scores = {}
        individual_scores = []
        
        try:
            # Get news sentiment from multi-source client
            sentiment_data = self.data_client.get_news_sentiment_multi_source(symbol)
            
            if sentiment_data and 'overall_sentiment' in sentiment_data:
                overall_sentiment = sentiment_data['overall_sentiment']
                
                # Convert sentiment score to 0-100 scale
                if overall_sentiment > 0.3:
                    sentiment_score = 80  # Very bullish news
                elif overall_sentiment > 0.1:
                    sentiment_score = 65  # Bullish news
                elif overall_sentiment > -0.1:
                    sentiment_score = 50  # Neutral news
                elif overall_sentiment > -0.3:
                    sentiment_score = 35  # Bearish news
                else:
                    sentiment_score = 20  # Very bearish news
                
                scores['news_sentiment'] = overall_sentiment
                individual_scores.append(sentiment_score)
            else:
                # No sentiment data available
                scores['news_sentiment'] = 0
                individual_scores.append(50)  # Neutral
            
            # Market sentiment based on recent price action
            # This would be calculated from market data trends
            # For now, use a neutral score
            market_sentiment_score = 50
            individual_scores.append(market_sentiment_score)
            
        except Exception as e:
            self.logger.error(f"Error calculating sentiment scores: {e}")
            individual_scores = [50] * 2  # Neutral scores on error
        
        scores['composite_sentiment_score'] = np.mean(individual_scores)
        return scores
    
    def calculate_composite_score(self, symbol: str, risk_profile: str = 'moderate') -> Dict[str, any]:
        """
        Calculate comprehensive composite score for trading decision
        
        Args:
            symbol: Cryptocurrency symbol
            risk_profile: Risk profile ('conservative', 'moderate', 'aggressive')
            
        Returns:
            Complete composite scoring analysis
        """
        try:
            self.logger.info(f"Calculating composite score for {symbol}")
            
            # Get market data
            data = self.data_client.get_crypto_data_multi_source(symbol, days=100)
            if data is None or data.empty:
                return {'error': f'No market data available for {symbol}'}
            
            # Calculate all indicator categories
            momentum_scores = self.calculate_momentum_score(data)
            trend_scores = self.calculate_trend_score(data)
            volatility_scores = self.calculate_volatility_score(data)
            volume_scores = self.calculate_volume_score(data)
            sentiment_scores = self.calculate_sentiment_score(symbol)
            
            # Calculate weighted composite score
            composite_score = (
                self.weights['momentum'] * momentum_scores['composite_momentum_score'] +
                self.weights['trend'] * trend_scores['composite_trend_score'] +
                self.weights['volatility'] * volatility_scores['composite_volatility_score'] +
                self.weights['volume'] * volume_scores['composite_volume_score'] +
                self.weights['sentiment'] * sentiment_scores['composite_sentiment_score']
            )
            
            # Generate trading recommendation
            recommendation = self._generate_recommendation(composite_score, risk_profile)
            confidence = self._calculate_confidence(momentum_scores, trend_scores, volatility_scores, volume_scores, sentiment_scores)
            
            # Calculate risk metrics
            risk_metrics = self._calculate_risk_metrics(data, volatility_scores)
            
            # Compile complete analysis
            analysis = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'composite_score': round(composite_score, 2),
                'recommendation': recommendation,
                'confidence': confidence,
                'risk_profile': risk_profile,
                'risk_metrics': risk_metrics,
                'category_scores': {
                    'momentum': round(momentum_scores['composite_momentum_score'], 2),
                    'trend': round(trend_scores['composite_trend_score'], 2),
                    'volatility': round(volatility_scores['composite_volatility_score'], 2),
                    'volume': round(volume_scores['composite_volume_score'], 2),
                    'sentiment': round(sentiment_scores['composite_sentiment_score'], 2)
                },
                'detailed_indicators': {
                    'momentum': momentum_scores,
                    'trend': trend_scores,
                    'volatility': volatility_scores,
                    'volume': volume_scores,
                    'sentiment': sentiment_scores
                },
                'weights_used': self.weights,
                'current_price': float(data['close'].iloc[-1]),
                'data_points': len(data)
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error calculating composite score for {symbol}: {e}")
            return {'error': str(e)}
    
    def _generate_recommendation(self, score: float, risk_profile: str) -> str:
        """Generate trading recommendation based on score and risk profile"""
        thresholds = self.risk_thresholds.get(risk_profile, self.risk_thresholds['moderate'])
        
        if score >= thresholds['min_score'] + 15:
            return 'Strong Buy'
        elif score >= thresholds['min_score']:
            return 'Buy'
        elif score <= (100 - thresholds['min_score']) - 15:
            return 'Strong Sell'
        elif score <= (100 - thresholds['min_score']):
            return 'Sell'
        else:
            return 'Hold'
    
    def _calculate_confidence(self, momentum: Dict, trend: Dict, volatility: Dict, volume: Dict, sentiment: Dict) -> str:
        """Calculate confidence level based on indicator agreement"""
        scores = [
            momentum.get('composite_momentum_score', 50),
            trend.get('composite_trend_score', 50),
            volatility.get('composite_volatility_score', 50),
            volume.get('composite_volume_score', 50),
            sentiment.get('composite_sentiment_score', 50)
        ]
        
        # Calculate standard deviation to measure agreement
        std_dev = np.std(scores)
        
        if std_dev < 10:
            return 'High'
        elif std_dev < 20:
            return 'Medium'
        else:
            return 'Low'
    
    def _calculate_risk_metrics(self, data: pd.DataFrame, volatility_scores: Dict) -> Dict[str, float]:
        """Calculate risk metrics for the trading decision"""
        try:
            close_prices = data['close']
            
            # Calculate daily returns
            returns = close_prices.pct_change().dropna()
            
            # Volatility (standard deviation of returns)
            volatility = returns.std() * np.sqrt(252)  # Annualized
            
            # Maximum drawdown
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = drawdown.min()
            
            # Sharpe ratio (assuming 0% risk-free rate)
            sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
            
            # Value at Risk (95% confidence)
            var_95 = np.percentile(returns, 5)
            
            return {
                'volatility': round(volatility, 4),
                'max_drawdown': round(max_drawdown, 4),
                'sharpe_ratio': round(sharpe_ratio, 4),
                'var_95': round(var_95, 4),
                'atr_percent': volatility_scores.get('atr_percent', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {e}")
            return {
                'volatility': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'var_95': 0,
                'atr_percent': 0
            }


# Example usage and testing
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Initialize composite scoring system
    scoring_system = CompositeScoring()
    
    print("🎯 Testing Composite Scoring System...")
    
    # Test composite scoring for BTC
    print("\n📊 Calculating composite score for BTC...")
    btc_analysis = scoring_system.calculate_composite_score('BTC', risk_profile='moderate')
    
    if 'error' not in btc_analysis:
        print(f"✅ BTC Composite Analysis Complete")
        print(f"📈 Current Price: ${btc_analysis['current_price']:.2f}")
        print(f"🎯 Composite Score: {btc_analysis['composite_score']}/100")
        print(f"💡 Recommendation: {btc_analysis['recommendation']}")
        print(f"🔒 Confidence: {btc_analysis['confidence']}")
        print(f"⚠️  Risk Profile: {btc_analysis['risk_profile']}")
        
        print(f"\n📊 Category Scores:")
        for category, score in btc_analysis['category_scores'].items():
            print(f"  {category.capitalize()}: {score}/100")
        
        print(f"\n⚠️  Risk Metrics:")
        risk = btc_analysis['risk_metrics']
        print(f"  Volatility: {risk['volatility']:.2%}")
        print(f"  Max Drawdown: {risk['max_drawdown']:.2%}")
        print(f"  Sharpe Ratio: {risk['sharpe_ratio']:.2f}")
        print(f"  VaR (95%): {risk['var_95']:.2%}")
        
    else:
        print(f"❌ BTC analysis failed: {btc_analysis['error']}")
    
    # Test multiple symbols
    print(f"\n🌍 Testing multiple cryptocurrencies...")
    symbols = ['ETH', 'SOL', 'ADA']
    
    for symbol in symbols:
        try:
            analysis = scoring_system.calculate_composite_score(symbol, risk_profile='moderate')
            if 'error' not in analysis:
                print(f"✅ {symbol}: {analysis['composite_score']}/100 - {analysis['recommendation']} ({analysis['confidence']} confidence)")
            else:
                print(f"❌ {symbol}: Analysis failed")
        except Exception as e:
            print(f"❌ {symbol}: Error - {e}")
    
    print(f"\n🎯 Composite scoring system test complete!")

