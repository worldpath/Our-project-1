"""
AlphaVantage API Client for Crypto Trading Bot Enhancement
Provides comprehensive crypto market data, technical indicators, and news sentiment
"""

import requests
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd

class AlphaVantageClient:
    """
    Enhanced AlphaVantage API client for cryptocurrency trading bot
    Provides technical indicators, market data, and news sentiment analysis
    """
    
    def __init__(self, api_key: str = "XPWO9DPRYM6V49W2"):
        """
        Initialize AlphaVantage client with API key
        
        Args:
            api_key: AlphaVantage API key (default from requirements)
        """
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.logger = logging.getLogger(__name__)
        
        # Rate limiting: 5 calls per minute for free tier
        self.last_call_time = 0
        self.min_call_interval = 12  # seconds between calls
        
        # Supported cryptocurrencies from AlphaVantage
        self.supported_cryptos = [
            'BTC', 'ETH', 'LTC', 'XRP', 'BCH', 'ADA', 'DOT', 'LINK',
            'BNB', 'XLM', 'USDC', 'USDT', 'DOGE', 'UNI', 'WBTC', 'AAVE',
            'SUSHI', 'SNX', 'MKR', 'COMP', 'YFI', 'ZRX', 'BAT', 'REP'
        ]
        
        # Technical indicators available
        self.available_indicators = [
            'RSI', 'MACD', 'STOCH', 'STOCHRSI', 'WILLR', 'ADX', 'ADXR',
            'APO', 'PPO', 'MOM', 'BOP', 'CCI', 'CMO', 'ROC', 'ROCR',
            'AROON', 'AROONOSC', 'MFI', 'TRIX', 'ULTOSC', 'DX', 'MINUS_DI',
            'PLUS_DI', 'MINUS_DM', 'PLUS_DM', 'BBANDS', 'MIDPOINT', 'MIDPRICE',
            'SAR', 'TRANGE', 'ATR', 'NATR', 'AD', 'ADOSC', 'OBV', 'HT_TRENDLINE',
            'HT_SINE', 'HT_TRENDMODE', 'HT_DCPERIOD', 'HT_DCPHASE', 'HT_PHASOR'
        ]
    
    def _rate_limit(self):
        """Implement rate limiting to avoid API quota issues"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        
        if time_since_last_call < self.min_call_interval:
            sleep_time = self.min_call_interval - time_since_last_call
            self.logger.info(f"Rate limiting: sleeping for {sleep_time:.1f} seconds")
            time.sleep(sleep_time)
        
        self.last_call_time = time.time()
    
    def _make_request(self, params: Dict) -> Optional[Dict]:
        """
        Make API request with error handling and rate limiting
        
        Args:
            params: API request parameters
            
        Returns:
            API response data or None if error
        """
        self._rate_limit()
        
        params['apikey'] = self.api_key
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if 'Error Message' in data:
                self.logger.error(f"AlphaVantage API error: {data['Error Message']}")
                return None
            
            if 'Note' in data:
                self.logger.warning(f"AlphaVantage API note: {data['Note']}")
                return None
            
            return data
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"AlphaVantage API request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"AlphaVantage API response parsing failed: {e}")
            return None
    
    def get_crypto_daily(self, symbol: str, market: str = "USD") -> Optional[pd.DataFrame]:
        """
        Get daily crypto price data
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC')
            market: Market currency (default: 'USD')
            
        Returns:
            DataFrame with OHLCV data or None if error
        """
        params = {
            'function': 'DIGITAL_CURRENCY_DAILY',
            'symbol': symbol,
            'market': market
        }
        
        data = self._make_request(params)
        if not data:
            return None
        
        try:
            # Find the time series key (format may vary)
            time_series_key = None
            for key in data.keys():
                if 'Time Series' in key and 'Digital Currency Daily' in key:
                    time_series_key = key
                    break
            
            if not time_series_key:
                self.logger.error(f"Time series data not found in response. Available keys: {list(data.keys())}")
                return None
            
            time_series = data[time_series_key]
            
            # Convert to DataFrame - handle different key formats
            df_data = []
            for date_str, values in time_series.items():
                try:
                    # Try different key formats
                    open_key = f'1a. open ({market})' if f'1a. open ({market})' in values else '1. open'
                    high_key = f'2a. high ({market})' if f'2a. high ({market})' in values else '2. high'
                    low_key = f'3a. low ({market})' if f'3a. low ({market})' in values else '3. low'
                    close_key = f'4a. close ({market})' if f'4a. close ({market})' in values else '4. close'
                    volume_key = '5. volume' if '5. volume' in values else 'volume'
                    
                    row = {
                        'date': pd.to_datetime(date_str),
                        'open': float(values[open_key]),
                        'high': float(values[high_key]),
                        'low': float(values[low_key]),
                        'close': float(values[close_key]),
                        'volume': float(values.get(volume_key, 0))
                    }
                    df_data.append(row)
                except (KeyError, ValueError) as e:
                    self.logger.warning(f"Skipping data point {date_str}: {e}")
                    continue
            
            if not df_data:
                self.logger.error("No valid data points found")
                return None
            
            df = pd.DataFrame(df_data)
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)
            
            self.logger.info(f"Retrieved {len(df)} days of data for {symbol}/{market}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error parsing crypto daily data: {e}")
            return None
    
    def get_crypto_intraday(self, symbol: str, interval: str = "5min", market: str = "USD") -> Optional[pd.DataFrame]:
        """
        Get intraday crypto price data
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC')
            interval: Time interval ('1min', '5min', '15min', '30min', '60min')
            market: Market currency (default: 'USD')
            
        Returns:
            DataFrame with OHLCV data or None if error
        """
        params = {
            'function': 'CRYPTO_INTRADAY',
            'symbol': symbol,
            'market': market,
            'interval': interval
        }
        
        data = self._make_request(params)
        if not data:
            return None
        
        try:
            time_series_key = f'Time Series Crypto ({interval})'
            if time_series_key not in data:
                self.logger.error(f"Expected key '{time_series_key}' not found in response")
                return None
            
            time_series = data[time_series_key]
            
            # Convert to DataFrame
            df_data = []
            for datetime_str, values in time_series.items():
                row = {
                    'datetime': pd.to_datetime(datetime_str),
                    'open': float(values['1. open']),
                    'high': float(values['2. high']),
                    'low': float(values['3. low']),
                    'close': float(values['4. close']),
                    'volume': float(values['5. volume'])
                }
                df_data.append(row)
            
            df = pd.DataFrame(df_data)
            df.set_index('datetime', inplace=True)
            df.sort_index(inplace=True)
            
            self.logger.info(f"Retrieved {len(df)} {interval} intervals for {symbol}/{market}")
            return df
            
        except (KeyError, ValueError) as e:
            self.logger.error(f"Error parsing crypto intraday data: {e}")
            return None
    
    def get_technical_indicator(self, symbol: str, indicator: str, interval: str = "daily", 
                              market: str = "USD", **kwargs) -> Optional[pd.DataFrame]:
        """
        Get technical indicator data for cryptocurrency
        
        Args:
            symbol: Cryptocurrency symbol
            indicator: Technical indicator name (e.g., 'RSI', 'MACD')
            interval: Time interval ('1min', '5min', '15min', '30min', '60min', 'daily', 'weekly', 'monthly')
            market: Market currency
            **kwargs: Additional indicator parameters
            
        Returns:
            DataFrame with indicator data or None if error
        """
        if indicator not in self.available_indicators:
            self.logger.error(f"Indicator '{indicator}' not supported")
            return None
        
        # For crypto, we need to use the crypto symbol format
        crypto_symbol = f"{symbol}{market}"
        
        params = {
            'function': indicator,
            'symbol': crypto_symbol,
            'interval': interval
        }
        
        # Add common indicator parameters
        if indicator == 'RSI':
            params['time_period'] = kwargs.get('time_period', 14)
            params['series_type'] = kwargs.get('series_type', 'close')
        elif indicator == 'MACD':
            params['series_type'] = kwargs.get('series_type', 'close')
            params['fastperiod'] = kwargs.get('fastperiod', 12)
            params['slowperiod'] = kwargs.get('slowperiod', 26)
            params['signalperiod'] = kwargs.get('signalperiod', 9)
        elif indicator == 'STOCH':
            params['fastkperiod'] = kwargs.get('fastkperiod', 5)
            params['slowkperiod'] = kwargs.get('slowkperiod', 3)
            params['slowdperiod'] = kwargs.get('slowdperiod', 3)
            params['slowkmatype'] = kwargs.get('slowkmatype', 0)
            params['slowdmatype'] = kwargs.get('slowdmatype', 0)
        
        # Add any additional parameters
        params.update(kwargs)
        
        data = self._make_request(params)
        if not data:
            return None
        
        try:
            # Find the technical analysis key - try multiple formats
            tech_key = None
            possible_keys = [
                f'Technical Analysis: {indicator}',
                f'Technical Analysis ({indicator})',
                indicator,
                f'{indicator} Values'
            ]
            
            for key in data.keys():
                if any(possible_key in key for possible_key in possible_keys):
                    tech_key = key
                    break
            
            if not tech_key:
                self.logger.error(f"Technical analysis data not found for {indicator}. Available keys: {list(data.keys())}")
                return None
            
            time_series = data[tech_key]
            
            # Convert to DataFrame
            df_data = []
            for datetime_str, values in time_series.items():
                row = {'datetime': pd.to_datetime(datetime_str)}
                
                # Handle different value key formats
                for k, v in values.items():
                    try:
                        # Clean up key names
                        clean_key = k.replace(f'{indicator} ', '').replace('(', '').replace(')', '')
                        row[clean_key] = float(v)
                    except (ValueError, TypeError):
                        continue
                
                if len(row) > 1:  # Only add if we have actual data
                    df_data.append(row)
            
            if not df_data:
                self.logger.error(f"No valid data points found for {indicator}")
                return None
            
            df = pd.DataFrame(df_data)
            df.set_index('datetime', inplace=True)
            df.sort_index(inplace=True)
            
            self.logger.info(f"Retrieved {indicator} data for {symbol}/{market}: {len(df)} points")
            return df
            
        except Exception as e:
            self.logger.error(f"Error parsing {indicator} data: {e}")
            return None
    
    def get_news_sentiment(self, topics: str = "cryptocurrency", limit: int = 50) -> Optional[List[Dict]]:
        """
        Get news sentiment analysis for cryptocurrency topics
        
        Args:
            topics: News topics to search (default: 'cryptocurrency')
            limit: Maximum number of articles (default: 50)
            
        Returns:
            List of news articles with sentiment scores or None if error
        """
        params = {
            'function': 'NEWS_SENTIMENT',
            'topics': topics,
            'limit': limit
        }
        
        data = self._make_request(params)
        if not data:
            return None
        
        try:
            if 'feed' not in data:
                self.logger.error("News feed data not found in response")
                return None
            
            articles = []
            for article in data['feed']:
                processed_article = {
                    'title': article.get('title', ''),
                    'url': article.get('url', ''),
                    'time_published': article.get('time_published', ''),
                    'authors': article.get('authors', []),
                    'summary': article.get('summary', ''),
                    'source': article.get('source', ''),
                    'category_within_source': article.get('category_within_source', ''),
                    'overall_sentiment_score': float(article.get('overall_sentiment_score', 0)),
                    'overall_sentiment_label': article.get('overall_sentiment_label', 'Neutral'),
                    'ticker_sentiment': article.get('ticker_sentiment', [])
                }
                articles.append(processed_article)
            
            self.logger.info(f"Retrieved {len(articles)} news articles with sentiment")
            return articles
            
        except (KeyError, ValueError) as e:
            self.logger.error(f"Error parsing news sentiment data: {e}")
            return None
    
    def get_crypto_rating(self, symbol: str) -> Optional[Dict]:
        """
        Get cryptocurrency rating and fundamental data
        
        Args:
            symbol: Cryptocurrency symbol
            
        Returns:
            Dictionary with rating data or None if error
        """
        params = {
            'function': 'CRYPTO_RATING',
            'symbol': symbol
        }
        
        data = self._make_request(params)
        if not data:
            return None
        
        try:
            if 'Crypto Rating (FCR)' not in data:
                self.logger.error("Crypto rating data not found in response")
                return None
            
            rating_data = data['Crypto Rating (FCR)']
            
            processed_rating = {
                'symbol': rating_data.get('1. symbol', ''),
                'name': rating_data.get('2. name', ''),
                'fcr_rating': rating_data.get('3. fcr rating', ''),
                'country': rating_data.get('4. country', ''),
                'sector': rating_data.get('5. sector', ''),
                'industry': rating_data.get('6. industry', ''),
                'address': rating_data.get('7. address', ''),
                'description': rating_data.get('8. description', ''),
                'cik': rating_data.get('9. cik', ''),
                'exchange': rating_data.get('10. exchange', ''),
                'currency': rating_data.get('11. currency', ''),
                'market_capitalization': rating_data.get('12. market capitalization', ''),
                'ebitda': rating_data.get('13. ebitda', ''),
                'pe_ratio': rating_data.get('14. pe ratio', ''),
                'peg_ratio': rating_data.get('15. peg ratio', ''),
                'book_value': rating_data.get('16. book value', '')
            }
            
            self.logger.info(f"Retrieved crypto rating for {symbol}")
            return processed_rating
            
        except (KeyError, ValueError) as e:
            self.logger.error(f"Error parsing crypto rating data: {e}")
            return None
    
    def get_multiple_indicators(self, symbol: str, indicators: List[str], 
                              interval: str = "daily", market: str = "USD") -> Dict[str, pd.DataFrame]:
        """
        Get multiple technical indicators for a cryptocurrency
        
        Args:
            symbol: Cryptocurrency symbol
            indicators: List of indicator names
            interval: Time interval
            market: Market currency
            
        Returns:
            Dictionary mapping indicator names to DataFrames
        """
        results = {}
        
        for indicator in indicators:
            self.logger.info(f"Fetching {indicator} for {symbol}")
            df = self.get_technical_indicator(symbol, indicator, interval, market)
            if df is not None:
                results[indicator] = df
            else:
                self.logger.warning(f"Failed to fetch {indicator} for {symbol}")
        
        return results
    
    def calculate_composite_score(self, symbol: str, weights: Dict[str, float] = None) -> Optional[Dict]:
        """
        Calculate composite trading score based on multiple indicators and sentiment
        
        Args:
            symbol: Cryptocurrency symbol
            weights: Dictionary of component weights (Technical/Sentiment/Momentum)
            
        Returns:
            Dictionary with composite score and components or None if error
        """
        if weights is None:
            weights = {
                'technical': 0.4,
                'sentiment': 0.3,
                'momentum': 0.3
            }
        
        try:
            # Get technical indicators
            technical_indicators = ['RSI', 'MACD', 'STOCH', 'ADX', 'CCI']
            tech_data = self.get_multiple_indicators(symbol, technical_indicators)
            
            # Calculate technical score (0-100)
            technical_score = self._calculate_technical_score(tech_data)
            
            # Get news sentiment
            news_data = self.get_news_sentiment(f"cryptocurrency {symbol}")
            sentiment_score = self._calculate_sentiment_score(news_data, symbol)
            
            # Get momentum indicators
            momentum_indicators = ['MOM', 'ROC', 'AROONOSC']
            momentum_data = self.get_multiple_indicators(symbol, momentum_indicators)
            momentum_score = self._calculate_momentum_score(momentum_data)
            
            # Calculate composite score
            composite_score = (
                technical_score * weights['technical'] +
                sentiment_score * weights['sentiment'] +
                momentum_score * weights['momentum']
            )
            
            result = {
                'symbol': symbol,
                'composite_score': round(composite_score, 2),
                'technical_score': round(technical_score, 2),
                'sentiment_score': round(sentiment_score, 2),
                'momentum_score': round(momentum_score, 2),
                'weights': weights,
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"Composite score for {symbol}: {composite_score:.2f}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating composite score for {symbol}: {e}")
            return None
    
    def _calculate_technical_score(self, tech_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate technical analysis score from indicators"""
        scores = []
        
        # RSI score (30-70 range is neutral, <30 oversold, >70 overbought)
        if 'RSI' in tech_data and not tech_data['RSI'].empty:
            rsi_value = tech_data['RSI'].iloc[-1]['RSI']
            if rsi_value < 30:
                scores.append(80)  # Oversold - potential buy
            elif rsi_value > 70:
                scores.append(20)  # Overbought - potential sell
            else:
                scores.append(50)  # Neutral
        
        # MACD score
        if 'MACD' in tech_data and not tech_data['MACD'].empty:
            macd_data = tech_data['MACD'].iloc[-1]
            if 'MACD' in macd_data and 'MACD_Signal' in macd_data:
                if macd_data['MACD'] > macd_data['MACD_Signal']:
                    scores.append(70)  # Bullish
                else:
                    scores.append(30)  # Bearish
        
        # Stochastic score
        if 'STOCH' in tech_data and not tech_data['STOCH'].empty:
            stoch_data = tech_data['STOCH'].iloc[-1]
            if 'SlowK' in stoch_data:
                stoch_k = stoch_data['SlowK']
                if stoch_k < 20:
                    scores.append(80)  # Oversold
                elif stoch_k > 80:
                    scores.append(20)  # Overbought
                else:
                    scores.append(50)  # Neutral
        
        return sum(scores) / len(scores) if scores else 50.0
    
    def _calculate_sentiment_score(self, news_data: List[Dict], symbol: str) -> float:
        """Calculate sentiment score from news data"""
        if not news_data:
            return 50.0  # Neutral if no news
        
        # Filter news relevant to the symbol
        relevant_scores = []
        for article in news_data:
            # Check if symbol is mentioned in ticker sentiment
            for ticker in article.get('ticker_sentiment', []):
                if ticker.get('ticker', '').upper() == symbol.upper():
                    sentiment_score = float(ticker.get('relevance_score', 0)) * 100
                    # Convert sentiment label to score
                    label = ticker.get('ticker_sentiment_label', 'Neutral')
                    if label == 'Bullish':
                        sentiment_score *= 1.5
                    elif label == 'Bearish':
                        sentiment_score *= 0.5
                    relevant_scores.append(sentiment_score)
            
            # Also use overall sentiment if symbol mentioned in title/summary
            if symbol.upper() in article.get('title', '').upper() or symbol.upper() in article.get('summary', '').upper():
                overall_score = (float(article.get('overall_sentiment_score', 0)) + 1) * 50  # Convert -1 to 1 range to 0-100
                relevant_scores.append(overall_score)
        
        return sum(relevant_scores) / len(relevant_scores) if relevant_scores else 50.0
    
    def _calculate_momentum_score(self, momentum_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate momentum score from momentum indicators"""
        scores = []
        
        # Momentum indicator
        if 'MOM' in momentum_data and not momentum_data['MOM'].empty:
            mom_value = momentum_data['MOM'].iloc[-1]['MOM']
            if mom_value > 0:
                scores.append(70)  # Positive momentum
            else:
                scores.append(30)  # Negative momentum
        
        # Rate of Change
        if 'ROC' in momentum_data and not momentum_data['ROC'].empty:
            roc_value = momentum_data['ROC'].iloc[-1]['ROC']
            if roc_value > 0:
                scores.append(70)  # Positive rate of change
            else:
                scores.append(30)  # Negative rate of change
        
        # Aroon Oscillator
        if 'AROONOSC' in momentum_data and not momentum_data['AROONOSC'].empty:
            aroon_value = momentum_data['AROONOSC'].iloc[-1]['AROON']
            if aroon_value > 0:
                scores.append(70)  # Uptrend
            else:
                scores.append(30)  # Downtrend
        
        return sum(scores) / len(scores) if scores else 50.0


# Example usage and testing
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize client
    client = AlphaVantageClient()
    
    # Test crypto data retrieval
    print("Testing AlphaVantage Crypto Integration...")
    
    # Test daily data
    btc_daily = client.get_crypto_daily('BTC')
    if btc_daily is not None:
        print(f"BTC Daily Data: {len(btc_daily)} days")
        print(btc_daily.tail())
    
    # Test technical indicators
    rsi_data = client.get_technical_indicator('BTC', 'RSI', interval='daily')
    if rsi_data is not None:
        print(f"BTC RSI Data: {len(rsi_data)} points")
        print(f"Latest RSI: {rsi_data.iloc[-1]['RSI']:.2f}")
    
    # Test news sentiment
    news = client.get_news_sentiment('cryptocurrency bitcoin')
    if news:
        print(f"Retrieved {len(news)} news articles")
        for article in news[:3]:
            print(f"- {article['title']}: {article['overall_sentiment_label']}")
    
    # Test composite score
    composite = client.calculate_composite_score('BTC')
    if composite:
        print(f"BTC Composite Score: {composite['composite_score']}")
        print(f"Technical: {composite['technical_score']}, Sentiment: {composite['sentiment_score']}, Momentum: {composite['momentum_score']}")

