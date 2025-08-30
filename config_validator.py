#!/usr/bin/env python3
"""
Configuration Validator for Crypto Trading Bot
============================================
Implements ChatGPT-5 Pro recommendations for safe configuration validation.
Ensures banner text matches actual runtime configuration.
"""

import os
import logging
from typing import Dict, Any, Optional
from bot_enhancements.risk_constraints import RiskConfig, Profile

# Load environment variables first
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class ConfigValidator:
    """Validates trading bot configuration for safety and consistency"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def validate_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and potentially adjust configuration based on ChatGPT-5 Pro recommendations
        
        Args:
            config: Configuration dictionary from environment/files
            
        Returns:
            Validated and safe configuration
            
        Raises:
            ValueError: If configuration is unsafe or invalid
        """
        
        # Extract risk settings
        profile = config.get('TRADING_MODE', 'moderate').lower()
        if profile == 'ultra_aggressive':
            profile = 'ultra'
            
        # Create RiskConfig to validate
        risk_config = RiskConfig(
            profile=profile,
            portfolio_risk=float(config.get('PORTFOLIO_RISK', 25.0)),
            max_position_size=float(config.get('MAX_POSITION_SIZE', 10.0)),
            risk_per_trade=float(config.get('RISK_PER_TRADE', 1.5)),
            max_daily_loss=float(config.get('MAX_DAILY_LOSS', 5.0)),
            max_drawdown=float(config.get('MAX_DRAWDOWN', 25.0)),
            max_concurrent_positions=int(config.get('MAX_CONCURRENT_POSITIONS', 5)),
            consecutive_loss_kill=int(config.get('CONSECUTIVE_LOSS_LIMIT', 7))
        )
        
        # Warn about ultra-aggressive settings
        if risk_config.profile == 'ultra':
            self.logger.warning("🚨 ULTRA-AGGRESSIVE MODE DETECTED!")
            self.logger.warning(f"Portfolio Risk: {risk_config.portfolio_risk}%")
            self.logger.warning(f"Max Position Size: {risk_config.max_position_size}%")
            self.logger.warning(f"Risk Per Trade: {risk_config.risk_per_trade}%")
            self.logger.warning("This configuration can result in significant losses!")
            
            # Require explicit confirmation for ultra mode
            if not config.get('ULTRA_MODE_CONFIRMED', False):
                raise ValueError(
                    "Ultra-aggressive mode requires explicit confirmation. "
                    "Set ULTRA_MODE_CONFIRMED=true in your environment to proceed."
                )
        
        # Check for dangerous mismatches
        self._check_banner_mismatch(risk_config)
        
        # Validate minimum notional for Binance.US
        min_notional = float(config.get('MIN_NOTIONAL_USD', 10.0))
        if min_notional < 10.0:
            self.logger.warning("Binance.US requires minimum $10 order size. Adjusting MIN_NOTIONAL_USD to 10.0")
            config['MIN_NOTIONAL_USD'] = 10.0
        
        # Validate liquidity requirements
        min_volume = float(config.get('MIN_VOLUME_24H_USD', 5_000_000))
        if min_volume < 1_000_000:
            self.logger.warning("Low minimum volume threshold may result in illiquid trading. Consider increasing MIN_VOLUME_24H_USD")
        
        # Update config with validated values
        config.update({
            'PORTFOLIO_RISK': risk_config.portfolio_risk,
            'MAX_POSITION_SIZE': risk_config.max_position_size,
            'RISK_PER_TRADE': risk_config.risk_per_trade,
            'MAX_DAILY_LOSS': risk_config.max_daily_loss,
            'MAX_DRAWDOWN': risk_config.max_drawdown,
            'MAX_CONCURRENT_POSITIONS': risk_config.max_concurrent_positions,
            'CONSECUTIVE_LOSS_LIMIT': risk_config.consecutive_loss_kill,
            'TRADING_MODE': risk_config.profile
        })
        
        self.logger.info(f"✅ Configuration validated - Profile: {risk_config.profile}")
        self.logger.info(f"Portfolio Risk: {risk_config.portfolio_risk}%, Position Size: {risk_config.max_position_size}%")
        
        return config
    
    def _check_banner_mismatch(self, risk_config: RiskConfig):
        """Check for dangerous banner vs actual config mismatches"""
        
        # The banner should match the actual configuration
        if risk_config.profile == 'moderate':
            if risk_config.portfolio_risk > 30 or risk_config.max_position_size > 15:
                self.logger.error("🚨 CRITICAL MISMATCH DETECTED!")
                self.logger.error("Banner claims moderate risk but configuration is aggressive!")
                self.logger.error(f"Actual: {risk_config.portfolio_risk}% portfolio, {risk_config.max_position_size}% position")
                self.logger.error("This could result in unexpected over-risking!")
        
        # Ultra settings should be explicitly labeled
        if (risk_config.portfolio_risk > 50 or 
            risk_config.max_position_size > 30 or 
            risk_config.risk_per_trade > 5.0):
            self.logger.warning("⚠️ EXTREME RISK SETTINGS DETECTED")
            self.logger.warning("Settings exceed typical aggressive thresholds")
    
    def load_and_validate_env_config(self) -> Dict[str, Any]:
        """Load configuration from environment and validate"""
        
        config = {}
        
        # Load all relevant environment variables
        env_vars = [
            'BINANCE_API_KEY', 'BINANCE_API_SECRET', 'PORTFOLIO_RISK', 'MAX_POSITION_SIZE',
            'RISK_PER_TRADE', 'MAX_DAILY_LOSS', 'MAX_DRAWDOWN', 'MAX_CONCURRENT_POSITIONS',
            'CONSECUTIVE_LOSS_LIMIT', 'TRADING_MODE', 'MIN_NOTIONAL_USD', 'MIN_VOLUME_24H_USD',
            'ULTRA_MODE_CONFIRMED', 'REAL_PORTFOLIO_VALUE', 'LIVE_TRADING'
        ]
        
        for var in env_vars:
            value = os.getenv(var)
            if value is not None:
                config[var] = value
        
        # Validate API credentials
        if not config.get('BINANCE_API_KEY') or not config.get('BINANCE_API_SECRET'):
            raise ValueError(
                "Missing Binance API credentials. Set BINANCE_API_KEY and BINANCE_API_SECRET"
            )
        
        # Validate and return
        return self.validate_configuration(config)
    
    def generate_startup_summary(self, config: Dict[str, Any]) -> str:
        """Generate a startup summary showing actual configuration"""
        
        summary = f"""
🤖 CRYPTO TRADING BOT STARTUP SUMMARY
=====================================

Profile: {config.get('TRADING_MODE', 'moderate').upper()}
Portfolio Risk: {config.get('PORTFOLIO_RISK', 25)}%
Max Position Size: {config.get('MAX_POSITION_SIZE', 10)}%
Risk Per Trade: {config.get('RISK_PER_TRADE', 1.5)}%
Max Daily Loss: {config.get('MAX_DAILY_LOSS', 5)}%
Max Drawdown: {config.get('MAX_DRAWDOWN', 25)}%

Live Trading: {config.get('LIVE_TRADING', 'false').upper()}
Portfolio Value: ${config.get('REAL_PORTFOLIO_VALUE', '10000')}

⚠️  These are your ACTUAL runtime settings!
"""
        
        if config.get('TRADING_MODE', '').lower() == 'ultra':
            summary += """
🚨 ULTRA-AGGRESSIVE MODE ACTIVE!
- Extreme risk settings enabled
- Potential for significant losses
- Monitor closely and ensure sufficient risk tolerance
"""
        
        return summary


if __name__ == "__main__":
    # Test configuration validation
    validator = ConfigValidator()
    try:
        config = validator.load_and_validate_env_config()
        print(validator.generate_startup_summary(config))
    except Exception as e:
        print(f"Configuration validation failed: {e}")