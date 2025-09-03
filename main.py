"""
Enhanced Crypto Trading Bot with Integrated Composite Scoring
Integrates with Enhanced Analysis Service v2.0 for professional trading decisions
Maintains live Binance.US trading with enhanced analysis capabilities
"""

import os
import sys
import time
import json
import logging
import requests
from alphavantage_client import AlphaVantageClient
import ccxt
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
from flask import Flask, jsonify, request
from flask_cors import CORS

class EnhancedTradingBot:
    """Enhanced Crypto Trading Bot with Composite Scoring Integration"""
    
    def __init__(self):
        """Initialize the enhanced trading bot"""
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/opt/crypto-bot/enhanced_trading_bot.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.api_key = os.getenv('BINANCE_US_API_KEY')
        self.api_secret = os.getenv('BINANCE_US_API_SECRET')
        
        if not self.api_key or not self.api_secret:
            self.logger.error("❌ Binance.US API credentials not found!")
            sys.exit(1)
        
        # Initialize Binance.US exchange
        self.exchange = ccxt.binanceus({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'sandbox': False,  # LIVE TRADING
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot'
            }
        })

        # Initialize AlphaVantage client for enhanced analysis
        try:
            self.alphavantage_client = AlphaVantageClient()
            self.logger.info("🔗 AlphaVantage client initialized for enhanced analysis")
        except Exception as e:
            self.logger.warning(f"⚠️ AlphaVantage client initialization failed: {e}")
            self.alphavantage_client = None
        
        # Trading configuration
        self.trading_pairs = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'ADA/USD', 'XRP/USD']
        self.base_currency = 'USD'
        self.min_trade_amount = 10.0
        self.max_position_size = 0.20  # 20% of portfolio per position
        self.portfolio_risk = 0.25  # 25% portfolio risk
        
        # Enhanced analysis integration
        self.analysis_service_url = 'http://localhost:8007'
        
        # Trading thresholds based on composite scores
        self.buy_threshold = 65.0    # Buy if score >= 65
        self.sell_threshold = 35.0   # Sell if score <= 35
        self.strong_buy_threshold = 75.0  # Strong buy if score >= 75
        self.strong_sell_threshold = 25.0  # Strong sell if score <= 25
        
        # Risk management
        self.stop_loss_pct = 0.05    # 5% stop loss
        self.take_profit_pct = 0.10  # 10% take profit
        self.max_daily_trades = 10
        self.daily_trade_count = 0
        self.last_trade_date = datetime.now().date()
        
        # Portfolio tracking
        self.portfolio_value = 0.0
        self.positions = {}
        self.trade_history = []
        
        # Control API
        self.app = Flask(__name__)
        CORS(self.app)
        self._setup_control_api()
        
        # Status
        self.is_trading = True
        self.last_analysis_time = None
        
        self.logger.info("🚀 Enhanced Trading Bot initialized with composite scoring integration")
    
    def get_enhanced_analysis(self, symbol: str) -> Dict:
        """Get enhanced analysis from Analysis Service v2.0 with AlphaVantage integration"""
        try:
            # Convert trading pair to symbol (BTC/USD -> BTC)
            base_symbol = symbol.split('/')[0]
            
            # Get base analysis from existing service
            response = requests.get(
                f"{self.analysis_service_url}/api/analysis/{base_symbol}",
                timeout=10
            )
            
            analysis = {}
            if response.status_code == 200:
                data = response.json()
                if 'error' not in data:
                    analysis = data
                else:
                    self.logger.warning(f"Analysis error for {symbol}: {data['error']}")
            else:
                self.logger.warning(f"Analysis service returned {response.status_code} for {symbol}")
            
            # Set default values if base analysis failed
            if not analysis:
                analysis = {
                    'composite_score': 50.0,
                    'recommendation': 'Hold',
                    'confidence': 'Low',
                    'risk_level': 'Medium',
                    'current_price': 0
                }
            
            # Enhance with AlphaVantage data if client is available
            if hasattr(self, 'alphavantage_client') and self.alphavantage_client:
                try:
                    self.logger.info(f"🔍 Getting AlphaVantage analysis for {base_symbol}")
                    av_analysis = self.alphavantage_client.calculate_composite_score(base_symbol)
                    
                    if av_analysis and 'composite_score' in av_analysis:
                        # Combine scores (weighted average: 60% existing, 40% AlphaVantage)
                        base_score = analysis.get('composite_score', 50.0)
                        av_score = av_analysis.get('composite_score', 50.0)
                        enhanced_score = (base_score * 0.6) + (av_score * 0.4)
                        
                        # Update analysis with AlphaVantage enhancements
                        analysis.update({
                            'composite_score': enhanced_score,
                            'alphavantage_score': av_score,
                            'base_score': base_score,
                            'alphavantage_confidence': av_analysis.get('confidence', 'Medium'),
                            'news_sentiment': av_analysis.get('sentiment_score', 50.0),
                            'technical_strength': av_analysis.get('technical_score', 50.0),
                            'enhanced': True
                        })
                        
                        # Adjust recommendation based on enhanced score
                        if enhanced_score >= 75:
                            analysis['recommendation'] = 'Strong Buy'
                            analysis['confidence'] = 'High'
                        elif enhanced_score >= 65:
                            analysis['recommendation'] = 'Buy'
                            analysis['confidence'] = 'Medium'
                        elif enhanced_score <= 25:
                            analysis['recommendation'] = 'Strong Sell'
                            analysis['confidence'] = 'High'
                        elif enhanced_score <= 35:
                            analysis['recommendation'] = 'Sell'
                            analysis['confidence'] = 'Medium'
                        
                        self.logger.info(f"📊 {symbol} Enhanced: Base={base_score:.1f}, AV={av_score:.1f}, Final={enhanced_score:.1f}")
                    else:
                        self.logger.warning(f"⚠️ AlphaVantage analysis unavailable for {symbol}")
                        analysis['enhanced'] = False
                        
                except Exception as e:
                    self.logger.warning(f"⚠️ AlphaVantage enhancement failed for {symbol}: {e}")
                    analysis['enhanced'] = False
            else:
                analysis['enhanced'] = False
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error getting enhanced analysis for {symbol}: {e}")
            # Return neutral analysis if everything fails
            return {
                'composite_score': 50.0,
                'recommendation': 'Hold',
                'confidence': 'Low',
                'risk_level': 'Medium',
                'current_price': 0,
                'enhanced': False
            }


    def get_portfolio_balance(self) -> float:
        """Get total portfolio value in USD"""
        try:
            balance = self.exchange.fetch_balance()
            total_value = 0.0
            
            # Add USD balance
            usd_balance = balance.get('USD', {}).get('free', 0)
            total_value += usd_balance
            
            # Add crypto holdings value
            for symbol in ['BTC', 'ETH', 'SOL', 'ADA', 'XRP']:
                crypto_balance = balance.get(symbol, {}).get('free', 0)
                if crypto_balance > 0:
                    try:
                        ticker = self.exchange.fetch_ticker(f'{symbol}/USD')
                        crypto_value = crypto_balance * ticker['last']
                        total_value += crypto_value
                        self.logger.info(f"💰 {symbol}: {crypto_balance:.6f} = ${crypto_value:.2f}")
                    except Exception as e:
                        self.logger.warning(f"Error getting {symbol} price: {e}")
            
            self.portfolio_value = total_value
            return total_value
            
        except Exception as e:
            self.logger.error(f"Error getting portfolio balance: {e}")
            return 0.0
    
    def calculate_position_size(self, symbol: str, analysis: Dict) -> float:
        """Calculate position size based on composite score and risk management"""
        try:
            composite_score = analysis.get('composite_score', 50.0)
            confidence = analysis.get('confidence', 'Low')
            risk_level = analysis.get('risk_level', 'Medium')
            
            # Base position size as percentage of portfolio
            base_size_pct = 0.10  # 10% base
            
            # Adjust based on composite score
            if composite_score >= self.strong_buy_threshold:
                size_multiplier = 2.0  # Strong signal = 2x position
            elif composite_score >= self.buy_threshold:
                size_multiplier = 1.5  # Buy signal = 1.5x position
            elif composite_score <= self.strong_sell_threshold:
                size_multiplier = 0.5  # Strong sell = reduce position
            elif composite_score <= self.sell_threshold:
                size_multiplier = 0.75  # Sell signal = reduce position
            else:
                size_multiplier = 1.0  # Hold = normal position
            
            # Adjust based on confidence
            confidence_multiplier = {
                'High': 1.2,
                'Medium': 1.0,
                'Low': 0.8
            }.get(confidence, 1.0)
            
            # Adjust based on risk level
            risk_multiplier = {
                'Low': 1.2,
                'Medium': 1.0,
                'High': 0.8,
                'Very High': 0.6
            }.get(risk_level, 1.0)
            
            # Calculate final position size
            position_size_pct = base_size_pct * size_multiplier * confidence_multiplier * risk_multiplier
            
            # Apply maximum position size limit
            position_size_pct = min(position_size_pct, self.max_position_size)
            
            # Calculate USD amount
            portfolio_value = self.get_portfolio_balance()
            position_size_usd = portfolio_value * position_size_pct
            
            # Apply minimum trade amount
            if position_size_usd < self.min_trade_amount:
                return 0.0
            
            self.logger.info(f"📊 {symbol} Position Size: {position_size_pct:.1%} = ${position_size_usd:.2f}")
            self.logger.info(f"   Score: {composite_score:.1f}, Confidence: {confidence}, Risk: {risk_level}")
            
            return position_size_usd
            
        except Exception as e:
            self.logger.error(f"Error calculating position size for {symbol}: {e}")
            return 0.0
    
    def execute_trade(self, symbol: str, side: str, amount_usd: float, analysis: Dict) -> bool:
        """Execute a trade based on enhanced analysis"""
        try:
            # Check daily trade limit
            current_date = datetime.now().date()
            if current_date != self.last_trade_date:
                self.daily_trade_count = 0
                self.last_trade_date = current_date
            
            if self.daily_trade_count >= self.max_daily_trades:
                self.logger.warning(f"⚠️ Daily trade limit reached ({self.max_daily_trades})")
                return False
            
            # Get current price
            ticker = self.exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            
            # Calculate quantity
            if side == 'buy':
                quantity = amount_usd / current_price
            else:  # sell
                # For sell, use available balance
                base_symbol = symbol.split('/')[0]
                balance = self.exchange.fetch_balance()
                available = balance.get(base_symbol, {}).get('free', 0)
                quantity = min(available, amount_usd / current_price)
            
            # Check minimum quantity
            market = self.exchange.market(symbol)
            min_amount = market.get('limits', {}).get('amount', {}).get('min', 0)
            
            if quantity < min_amount:
                self.logger.warning(f"⚠️ Quantity {quantity} below minimum {min_amount} for {symbol}")
                return False
            
            # Execute the trade
            self.logger.info(f"🔄 Executing {side.upper()} order: {quantity:.6f} {symbol} at ${current_price:.2f}")
            
            order = self.exchange.create_market_order(symbol, side, quantity)
            
            if order and order.get('id'):
                self.daily_trade_count += 1
                
                # Log trade details
                trade_info = {
                    'timestamp': datetime.now().isoformat(),
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'price': current_price,
                    'amount_usd': amount_usd,
                    'order_id': order['id'],
                    'composite_score': analysis.get('composite_score', 0),
                    'recommendation': analysis.get('recommendation', 'Unknown'),
                    'confidence': analysis.get('confidence', 'Unknown')
                }
                
                self.trade_history.append(trade_info)
                
                self.logger.info(f"✅ Trade executed successfully!")
                self.logger.info(f"   Order ID: {order['id']}")
                self.logger.info(f"   Composite Score: {analysis.get('composite_score', 0):.1f}")
                self.logger.info(f"   Recommendation: {analysis.get('recommendation', 'Unknown')}")
                
                return True
            else:
                self.logger.error(f"❌ Trade execution failed for {symbol}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error executing trade for {symbol}: {e}")
            return False
    
    def analyze_and_trade(self, symbol: str):
        """Analyze a symbol and execute trades based on composite scoring"""
        try:
            if not self.is_trading:
                return
            
            self.logger.info(f"🔍 Analyzing {symbol} with enhanced composite scoring...")
            
            # Get enhanced analysis
            analysis = self.get_enhanced_analysis(symbol)
            composite_score = analysis.get('composite_score', 50.0)
            recommendation = analysis.get('recommendation', 'Hold')
            confidence = analysis.get('confidence', 'Low')
            risk_level = analysis.get('risk_level', 'Medium')
            
            self.logger.info(f"📊 {symbol} Analysis Results:")
            self.logger.info(f"   Composite Score: {composite_score:.1f}/100")
            self.logger.info(f"   Recommendation: {recommendation}")
            self.logger.info(f"   Confidence: {confidence}")
            self.logger.info(f"   Risk Level: {risk_level}")
            
            # Only trade with Medium+ confidence
            if confidence == 'Low':
                self.logger.info(f"⚠️ Skipping {symbol} due to low confidence")
                return
            
            # Get current position
            base_symbol = symbol.split('/')[0]
            balance = self.exchange.fetch_balance()
            current_position = balance.get(base_symbol, {}).get('free', 0)
            
            # Calculate position size
            target_position_usd = self.calculate_position_size(symbol, analysis)
            
            # Trading logic based on composite score
            if composite_score >= self.buy_threshold and target_position_usd > 0:
                # BUY SIGNAL
                if current_position == 0 or composite_score >= self.strong_buy_threshold:
                    self.logger.info(f"🟢 BUY SIGNAL for {symbol} (Score: {composite_score:.1f})")
                    success = self.execute_trade(symbol, 'buy', target_position_usd, analysis)
                    if success:
                        self.logger.info(f"✅ Bought {symbol} based on composite score {composite_score:.1f}")
                else:
                    self.logger.info(f"📈 {symbol} buy signal but already have position")
            
            elif composite_score <= self.sell_threshold and current_position > 0:
                # SELL SIGNAL
                ticker = self.exchange.fetch_ticker(symbol)
                position_value = current_position * ticker['last']
                
                if position_value >= self.min_trade_amount:
                    self.logger.info(f"🔴 SELL SIGNAL for {symbol} (Score: {composite_score:.1f})")
                    success = self.execute_trade(symbol, 'sell', position_value, analysis)
                    if success:
                        self.logger.info(f"✅ Sold {symbol} based on composite score {composite_score:.1f}")
                else:
                    self.logger.info(f"📉 {symbol} sell signal but position too small")
            
            else:
                # HOLD
                self.logger.info(f"⚪ HOLD {symbol} (Score: {composite_score:.1f})")
            
        except Exception as e:
            self.logger.error(f"❌ Error analyzing {symbol}: {e}")
    
    def trading_cycle(self):
        """Main trading cycle with enhanced analysis"""
        try:
            self.logger.info("🔄 Starting enhanced trading cycle...")
            
            # Update portfolio value
            portfolio_value = self.get_portfolio_balance()
            self.logger.info(f"💰 Current Portfolio Value: ${portfolio_value:.2f}")
            
            if portfolio_value < self.min_trade_amount:
                self.logger.warning("⚠️ Portfolio value too low for trading")
                return
            
            # Analyze each trading pair
            for symbol in self.trading_pairs:
                if self.is_trading:
                    self.analyze_and_trade(symbol)
                    time.sleep(2)  # Rate limiting
            
            self.last_analysis_time = datetime.now()
            self.logger.info("✅ Enhanced trading cycle completed")
            
        except Exception as e:
            self.logger.error(f"❌ Error in trading cycle: {e}")
    
    def _setup_control_api(self):
        """Setup control API endpoints"""
        
        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            """Get bot status"""
            return jsonify({
                'status': 'active' if self.is_trading else 'paused',
                'portfolio_value': self.portfolio_value,
                'trading_mode': 'LIVE_ENHANCED',
                'exchange': 'Binance.US',
                'version': '3.0-Enhanced',
                'last_analysis': self.last_analysis_time.isoformat() if self.last_analysis_time else None,
                'daily_trades': self.daily_trade_count,
                'max_daily_trades': self.max_daily_trades,
                'analysis_service': self.analysis_service_url,
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/api/portfolio', methods=['GET'])
        def get_portfolio():
            """Get detailed portfolio information"""
            try:
                balance = self.exchange.fetch_balance()
                portfolio = {
                    'total_value': self.get_portfolio_balance(),
                    'cash_balance': balance.get('USD', {}).get('free', 0),
                    'positions': {},
                    'timestamp': datetime.now().isoformat()
                }
                
                for symbol in ['BTC', 'ETH', 'SOL', 'ADA', 'XRP']:
                    crypto_balance = balance.get(symbol, {}).get('free', 0)
                    if crypto_balance > 0:
                        try:
                            ticker = self.exchange.fetch_ticker(f'{symbol}/USD')
                            value = crypto_balance * ticker['last']
                            portfolio['positions'][symbol] = {
                                'quantity': crypto_balance,
                                'price': ticker['last'],
                                'value': value
                            }
                        except:
                            pass
                
                return jsonify(portfolio)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/trades', methods=['GET'])
        def get_trades():
            """Get recent trade history"""
            return jsonify({
                'trades': self.trade_history[-20:],  # Last 20 trades
                'total_trades': len(self.trade_history),
                'daily_trades': self.daily_trade_count
            })
        
        @self.app.route('/api/analysis/<symbol>', methods=['GET'])
        def get_symbol_analysis(symbol):
            """Get enhanced analysis for a specific symbol"""
            try:
                analysis = self.get_enhanced_analysis(f"{symbol}/USD")
                return jsonify(analysis)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/control/pause', methods=['POST'])
        def pause_trading():
            """Pause trading"""
            self.is_trading = False
            self.logger.info("⏸️ Trading paused via API")
            return jsonify({'status': 'paused'})
        
        @self.app.route('/api/control/resume', methods=['POST'])
        def resume_trading():
            """Resume trading"""
            self.is_trading = True
            self.logger.info("▶️ Trading resumed via API")
            return jsonify({'status': 'active'})
        
        @self.app.route('/api/control/emergency-stop', methods=['POST'])
        def emergency_stop():
            """Emergency stop - pause trading and sell all positions"""
            self.is_trading = False
            self.logger.warning("🚨 EMERGENCY STOP activated via API")
            
            # TODO: Implement emergency sell logic if needed
            
            return jsonify({'status': 'emergency_stopped'})
    
    def run_control_api(self):
        """Run the control API in a separate thread"""
        self.app.run(host='0.0.0.0', port=8008, debug=False)
    
    def run(self):
        """Run the enhanced trading bot"""
        self.logger.info("🚀 Starting Enhanced Crypto Trading Bot v3.0...")
        
        # Start control API in background
        api_thread = threading.Thread(target=self.run_control_api, daemon=True)
        api_thread.start()
        
        # Test exchange connection
        try:
            balance = self.exchange.fetch_balance()
            self.logger.info("✅ Binance.US connection successful")
            self.logger.info(f"💰 Initial Portfolio Value: ${self.get_portfolio_balance():.2f}")
        except Exception as e:
            self.logger.error(f"❌ Exchange connection failed: {e}")
            return
        
        # Test enhanced analysis service
        try:
            response = requests.get(f"{self.analysis_service_url}/api/status", timeout=5)
            if response.status_code == 200:
                self.logger.info("✅ Enhanced Analysis Service connected")
            else:
                self.logger.warning("⚠️ Enhanced Analysis Service not responding")
        except Exception as e:
            self.logger.warning(f"⚠️ Enhanced Analysis Service connection failed: {e}")
        
        # Main trading loop
        self.logger.info("🔄 Starting enhanced trading loop...")
        
        while True:
            try:
                if self.is_trading:
                    self.trading_cycle()
                
                # Wait 5 minutes between cycles
                time.sleep(300)
                
            except KeyboardInterrupt:
                self.logger.info("👋 Shutting down Enhanced Trading Bot...")
                break
            except Exception as e:
                self.logger.error(f"❌ Unexpected error in main loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying


if __name__ == "__main__":
    bot = EnhancedTradingBot()
    bot.run()

