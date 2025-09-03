"""
Multi-Source Data Client for Enhanced Crypto Trading Bot
Integrates Yahoo Finance, AlphaVantage, and Binance data sources
Provides robust, redundant data access with fallback mechanisms
"""

import logging
import numpy as np
import pandas as pd
import yfinance as yf
import ccxt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from alphavantage_client import AlphaVantageClient

class MultiSourceDataClient:
    """
    Multi-source data client that combines Yahoo Finance, AlphaVantage, and Binance
    Provides redundant data access with intelligent fallback mechanisms
    """
    
    def __init__(self, alphavantage_api_key: str = "XPWO9DPRYM6V49W2", 
                 binance_api_key: str = None, binance_secret: str = None):
        """
        Initialize multi-source data client
        
        Args:
            alphavantage_api_key: AlphaVantage API key
            binance_api_key: Binance API key (optional)
            binance_secret: Binance API secret (optional)
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize data sources
        self.av_client = AlphaVantageClient(alphavantage_api_key)
        
        # Initialize Binance client
        self.binance_client = None
        if binance_api_key and binance_secret:
            try:
                self.binance_client = ccxt.binanceus({
                    'apiKey': binance_api_key,
                    'secret': binance_secret,
                    'sandbox': False,
                    'enableRateLimit': True
                })
                self.logger.info("Binance client initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize Binance client: {e}")
        
        # Cache for data to reduce API calls
        self.data_cache = {}
        self.cache_expiry = {}
        self.cache_duration = 300  # 5 minutes
        
        # Yahoo Finance crypto symbol mappings
        self.yf_crypto_symbols = {
            'BTC': 'BTC-USD',
            'ETH': 'ETH-USD',
            'LTC': 'LTC-USD',
            'XRP': 'XRP-USD',
            'BCH': 'BCH-USD',
            'ADA': 'ADA-USD',
            'DOT': 'DOT-USD',
            'LINK': 'LINK-USD',
            'BNB': 'BNB-USD',
            'XLM': 'XLM-USD',
            'DOGE': 'DOGE-USD',
            'UNI': 'UNI-USD',
            'AAVE': 'AAVE-USD',
            'SUSHI': 'SUSHI-USD',
            'MKR': 'MKR-USD',
            'COMP': 'COMP-USD',
            'YFI': 'YFI-USD',
            'SOL': 'SOL-USD',
            'AVAX': 'AVAX-USD',
            'MATIC': 'MATIC-USD'
        }
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.cache_expiry:
            return False
        return datetime.now() < self.cache_expiry[cache_key]
    
    def _cache_data(self, cache_key: str, data: any):
        """Cache data with expiry time"""
        self.data_cache[cache_key] = data
        self.cache_expiry[cache_key] = datetime.now() + timedelta(seconds=self.cache_duration)
    
    def get_crypto_data_yahoo(self, symbol: str, period: str = "1y", interval: str = "1d") -> Optional[pd.DataFrame]:
        """
        Get cryptocurrency data from Yahoo Finance
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC')
            period: Data period ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
            interval: Data interval ('1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo')
            
        Returns:
            DataFrame with OHLCV data or None if error
        """
        try:
            # Convert symbol to Yahoo Finance format
            yf_symbol = self.yf_crypto_symbols.get(symbol, f"{symbol}-USD")
            
            # Create ticker object
            ticker = yf.Ticker(yf_symbol)
            
            # Get historical data
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                self.logger.warning(f"No data returned from Yahoo Finance for {yf_symbol}")
                return None
            
            # Standardize column names
            data.columns = [col.lower() for col in data.columns]
            
            # Ensure we have the required columns
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in data.columns for col in required_columns):
                self.logger.error(f"Missing required columns in Yahoo Finance data for {yf_symbol}")
                return None
            
            self.logger.info(f"Retrieved {len(data)} data points from Yahoo Finance for {yf_symbol}")
            return data[required_columns]
            
        except Exception as e:
            self.logger.error(f"Error getting Yahoo Finance data for {symbol}: {e}")
            return None
    
    def get_crypto_data_binance(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> Optional[pd.DataFrame]:
        """
        Get cryptocurrency data from Binance
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC')
            timeframe: Timeframe ('1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w')
            limit: Number of data points to retrieve
            
        Returns:
            DataFrame with OHLCV data or None if error
        """
        if not self.binance_client:
            self.logger.warning("Binance client not initialized")
            return None
        
        try:
            # Convert symbol to Binance format
            binance_symbol = f"{symbol}/USD"
            
            # Get OHLCV data
            ohlcv = self.binance_client.fetch_ohlcv(binance_symbol, timeframe, limit=limit)
            
            if not ohlcv:
                self.logger.warning(f"No data returned from Binance for {binance_symbol}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            self.logger.info(f"Retrieved {len(df)} data points from Binance for {binance_symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error getting Binance data for {symbol}: {e}")
            return None
    
    def get_crypto_data_multi_source(self, symbol: str, days: int = 100) -> Optional[pd.DataFrame]:
        """
        Get cryptocurrency data using multiple sources with fallback
        
        Args:
            symbol: Cryptocurrency symbol
            days: Number of days of data to retrieve
            
        Returns:
            DataFrame with OHLCV data from the best available source
        """
        cache_key = f"{symbol}_multi_data_{days}d"
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            self.logger.info(f"Using cached multi-source data for {symbol}")
            return self.data_cache[cache_key]
        
        data = None
        source_used = None
        
        # Try Yahoo Finance first (most reliable for crypto)
        try:
            self.logger.info(f"Attempting to get {symbol} data from Yahoo Finance...")
            data = self.get_crypto_data_yahoo(symbol, period=f"{days}d" if days <= 730 else "max")
            if data is not None and not data.empty:
                source_used = "Yahoo Finance"
                # Limit to requested days
                if len(data) > days:
                    data = data.tail(days)
        except Exception as e:
            self.logger.error(f"Yahoo Finance failed for {symbol}: {e}")
        
        # Fallback to Binance if Yahoo Finance fails
        if data is None or data.empty:
            try:
                self.logger.info(f"Falling back to Binance for {symbol}...")
                data = self.get_crypto_data_binance(symbol, limit=min(days, 1000))
                if data is not None and not data.empty:
                    source_used = "Binance"
            except Exception as e:
                self.logger.error(f"Binance fallback failed for {symbol}: {e}")
        
        # Fallback to AlphaVantage if both fail
        if data is None or data.empty:
            try:
                self.logger.info(f"Falling back to AlphaVantage for {symbol}...")
                data = self.av_client.get_crypto_daily(symbol)
                if data is not None and not data.empty:
                    source_used = "AlphaVantage"
                    # Limit to requested days
                    if len(data) > days:
                        data = data.tail(days)
            except Exception as e:
                self.logger.error(f"AlphaVantage fallback failed for {symbol}: {e}")
        
        if data is not None and not data.empty:
            self.logger.info(f"Successfully retrieved {len(data)} days of {symbol} data from {source_used}")
            self._cache_data(cache_key, data)
            return data
        else:
            self.logger.error(f"Failed to retrieve data for {symbol} from all sources")
            return None
    
    def get_market_data_yahoo(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Get current market data for multiple symbols from Yahoo Finance
        
        Args:
            symbols: List of cryptocurrency symbols
            
        Returns:
            Dictionary with market data for each symbol
        """
        market_data = {}
        
        for symbol in symbols:
            try:
                yf_symbol = self.yf_crypto_symbols.get(symbol, f"{symbol}-USD")
                ticker = yf.Ticker(yf_symbol)
                
                # Get current info
                info = ticker.info
                
                # Get recent price data
                hist = ticker.history(period="2d", interval="1d")
                
                if not hist.empty:
                    current_price = float(hist['Close'].iloc[-1])
                    previous_price = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
                    
                    market_data[symbol] = {
                        'current_price': current_price,
                        'previous_close': previous_price,
                        'change': current_price - previous_price,
                        'change_percent': ((current_price / previous_price) - 1) * 100 if previous_price > 0 else 0,
                        'volume': float(hist['Volume'].iloc[-1]) if 'Volume' in hist.columns else 0,
                        'market_cap': info.get('marketCap', 0),
                        'source': 'Yahoo Finance'
                    }
                    
                    self.logger.info(f"Retrieved market data for {symbol}: ${current_price:.2f}")
                
            except Exception as e:
                self.logger.error(f"Error getting market data for {symbol}: {e}")
                market_data[symbol] = {'error': str(e)}
        
        return market_data
    
    def get_news_sentiment_multi_source(self, symbol: str) -> Dict[str, any]:
        """
        Get news sentiment from multiple sources
        
        Args:
            symbol: Cryptocurrency symbol
            
        Returns:
            Combined news sentiment analysis
        """
        sentiment_data = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'sources': {}
        }
        
        # Get AlphaVantage news sentiment
        try:
            av_news = self.av_client.get_news_sentiment(f"cryptocurrency {symbol}")
            if av_news:
                sentiment_scores = [article['overall_sentiment_score'] for article in av_news]
                avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0
                
                sentiment_data['sources']['alphavantage'] = {
                    'article_count': len(av_news),
                    'average_sentiment': avg_sentiment,
                    'sentiment_label': 'Bullish' if avg_sentiment > 0.1 else 'Bearish' if avg_sentiment < -0.1 else 'Neutral',
                    'recent_articles': av_news[:5]  # Keep 5 most recent
                }
                
                self.logger.info(f"Retrieved {len(av_news)} news articles from AlphaVantage for {symbol}")
        except Exception as e:
            self.logger.error(f"Error getting AlphaVantage news for {symbol}: {e}")
            sentiment_data['sources']['alphavantage'] = {'error': str(e)}
        
        # Calculate overall sentiment
        sentiment_scores = []
        for source, data in sentiment_data['sources'].items():
            if 'average_sentiment' in data:
                sentiment_scores.append(data['average_sentiment'])
        
        if sentiment_scores:
            sentiment_data['overall_sentiment'] = np.mean(sentiment_scores)
            sentiment_data['overall_label'] = (
                'Bullish' if sentiment_data['overall_sentiment'] > 0.1 
                else 'Bearish' if sentiment_data['overall_sentiment'] < -0.1 
                else 'Neutral'
            )
        else:
            sentiment_data['overall_sentiment'] = 0
            sentiment_data['overall_label'] = 'Neutral'
        
        return sentiment_data
    
    def get_comprehensive_market_overview(self, symbols: List[str]) -> Dict[str, any]:
        """
        Get comprehensive market overview using all data sources
        
        Args:
            symbols: List of cryptocurrency symbols to analyze
            
        Returns:
            Comprehensive market overview
        """
        overview = {
            'timestamp': datetime.now().isoformat(),
            'symbols_analyzed': symbols,
            'market_data': {},
            'sentiment_analysis': {},
            'data_sources_used': []
        }
        
        # Get market data from Yahoo Finance
        try:
            market_data = self.get_market_data_yahoo(symbols)
            overview['market_data'] = market_data
            if market_data:
                overview['data_sources_used'].append('Yahoo Finance')
        except Exception as e:
            self.logger.error(f"Error getting market overview from Yahoo Finance: {e}")
        
        # Get sentiment analysis for each symbol
        for symbol in symbols:
            try:
                sentiment = self.get_news_sentiment_multi_source(symbol)
                overview['sentiment_analysis'][symbol] = sentiment
                if 'alphavantage' in sentiment.get('sources', {}):
                    if 'AlphaVantage' not in overview['data_sources_used']:
                        overview['data_sources_used'].append('AlphaVantage')
            except Exception as e:
                self.logger.error(f"Error getting sentiment for {symbol}: {e}")
        
        # Calculate market summary
        try:
            prices = [data.get('current_price', 0) for data in overview['market_data'].values() if 'current_price' in data]
            changes = [data.get('change_percent', 0) for data in overview['market_data'].values() if 'change_percent' in data]
            
            overview['market_summary'] = {
                'total_symbols': len(symbols),
                'successful_retrievals': len([d for d in overview['market_data'].values() if 'current_price' in d]),
                'average_change_percent': np.mean(changes) if changes else 0,
                'bullish_count': len([c for c in changes if c > 0]),
                'bearish_count': len([c for c in changes if c < 0]),
                'market_sentiment': 'Bullish' if len([c for c in changes if c > 0]) > len([c for c in changes if c < 0]) else 'Bearish'
            }
        except Exception as e:
            self.logger.error(f"Error calculating market summary: {e}")
        
        return overview
    
    def test_all_sources(self) -> Dict[str, bool]:
        """
        Test connectivity to all data sources
        
        Returns:
            Dictionary showing which sources are working
        """
        results = {}
        
        # Test Yahoo Finance
        try:
            test_data = self.get_crypto_data_yahoo('BTC', period='5d')
            results['yahoo_finance'] = test_data is not None and not test_data.empty
        except Exception as e:
            self.logger.error(f"Yahoo Finance test failed: {e}")
            results['yahoo_finance'] = False
        
        # Test Binance
        try:
            if self.binance_client:
                test_data = self.get_crypto_data_binance('BTC', limit=5)
                results['binance'] = test_data is not None and not test_data.empty
            else:
                results['binance'] = False
        except Exception as e:
            self.logger.error(f"Binance test failed: {e}")
            results['binance'] = False
        
        # Test AlphaVantage
        try:
            test_data = self.av_client.get_crypto_daily('BTC')
            results['alphavantage'] = test_data is not None and not test_data.empty
        except Exception as e:
            self.logger.error(f"AlphaVantage test failed: {e}")
            results['alphavantage'] = False
        
        return results


# Example usage and testing
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Initialize multi-source client
    client = MultiSourceDataClient()
    
    print("🔄 Testing Multi-Source Data Client...")
    
    # Test all sources
    print("\n📊 Testing data source connectivity...")
    source_status = client.test_all_sources()
    for source, status in source_status.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {source.replace('_', ' ').title()}: {'Working' if status else 'Failed'}")
    
    # Test Yahoo Finance crypto data
    print("\n📈 Testing Yahoo Finance crypto data...")
    btc_data = client.get_crypto_data_yahoo('BTC', period='30d')
    if btc_data is not None:
        print(f"✅ BTC data from Yahoo Finance: {len(btc_data)} days")
        print(f"Latest BTC price: ${btc_data['close'].iloc[-1]:.2f}")
        print(f"30-day change: {((btc_data['close'].iloc[-1] / btc_data['close'].iloc[0]) - 1) * 100:.2f}%")
    else:
        print("❌ Failed to get BTC data from Yahoo Finance")
    
    # Test multi-source data retrieval
    print("\n🔄 Testing multi-source data retrieval...")
    multi_data = client.get_crypto_data_multi_source('BTC', days=30)
    if multi_data is not None:
        print(f"✅ Multi-source BTC data: {len(multi_data)} days")
        print(f"Data range: {multi_data.index[0]} to {multi_data.index[-1]}")
    else:
        print("❌ Failed to get BTC data from any source")
    
    # Test market data for multiple symbols
    print("\n📊 Testing market data for multiple symbols...")
    symbols = ['BTC', 'ETH', 'SOL', 'ADA']
    market_data = client.get_market_data_yahoo(symbols)
    for symbol, data in market_data.items():
        if 'current_price' in data:
            print(f"✅ {symbol}: ${data['current_price']:.2f} ({data['change_percent']:+.2f}%)")
        else:
            print(f"❌ {symbol}: Failed to retrieve data")
    
    # Test comprehensive market overview
    print("\n🌍 Testing comprehensive market overview...")
    overview = client.get_comprehensive_market_overview(['BTC', 'ETH'])
    if overview:
        print(f"✅ Market overview generated")
        print(f"Data sources used: {', '.join(overview['data_sources_used'])}")
        if 'market_summary' in overview:
            summary = overview['market_summary']
            print(f"Market sentiment: {summary.get('market_sentiment', 'Unknown')}")
            print(f"Average change: {summary.get('average_change_percent', 0):.2f}%")
    
    print("\n🎯 Multi-source data client test complete!")

