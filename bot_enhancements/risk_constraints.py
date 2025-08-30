from pydantic import BaseModel, Field, model_validator
from typing import Literal

Profile = Literal['conservative','moderate','aggressive','ultra']

class RiskConfig(BaseModel):
    profile: Profile = 'moderate'
    portfolio_risk: float = Field(25.0, ge=0, le=100)
    max_position_size: float = Field(10.0, ge=0, le=100)
    risk_per_trade: float = Field(1.5, ge=0, le=100)
    max_daily_loss: float = Field(5.0, ge=0, le=100)
    max_drawdown: float = Field(25.0, ge=0, le=100)
    max_concurrent_positions: int = Field(5, ge=1, le=50)
    consecutive_loss_kill: int = Field(7, ge=1, le=50)

    @model_validator(mode='after')
    def validate_profile(self):
        p = self.profile
        # Upper bounds by profile
        caps = {
            'conservative': dict(portfolio_risk=15, max_position_size=5, risk_per_trade=0.5),
            'moderate':     dict(portfolio_risk=25, max_position_size=10, risk_per_trade=1.0),
            'aggressive':   dict(portfolio_risk=35, max_position_size=15, risk_per_trade=2.0),
            'ultra':        dict(portfolio_risk=45, max_position_size=20, risk_per_trade=3.0),
        }
        c = caps[p]
        self.portfolio_risk = min(self.portfolio_risk, c['portfolio_risk'])
        self.max_position_size = min(self.max_position_size, c['max_position_size'])
        self.risk_per_trade = min(self.risk_per_trade, c['risk_per_trade'])
        return self