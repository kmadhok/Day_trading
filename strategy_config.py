from enum import Enum
from dataclasses import dataclass
from typing import Optional


class StrategyType(Enum):
    """Strategy types available in the trading system."""
    CURRENT = "current"
    AGGRESSIVE = "aggressive"
    CONSERVATIVE = "conservative"


@dataclass
class StrategyConfig:
    """Configuration class for trading strategies."""
    name: str
    strategy_type: StrategyType
    
    # RSI parameters
    rsi_buy_threshold: float
    rsi_sell_threshold: float
    
    # MACD parameters
    macd_require_zero_cross: bool
    
    # Trend filter parameters
    trend_confirmation_periods: int
    
    # Signal combination requirements
    indicators_required: int  # How many of the 3 indicators must align
    
    # Volume filter (only for conservative)
    use_volume_filter: bool
    
    # Description for reporting
    description: str
    
    # Volume parameters (after required fields)
    volume_lookback_periods: Optional[int] = None


def get_strategy_config(strategy_type: StrategyType) -> StrategyConfig:
    """
    Get configuration for a specific strategy type.
    
    Args:
        strategy_type (StrategyType): The strategy type
        
    Returns:
        StrategyConfig: Strategy configuration
    """
    if strategy_type == StrategyType.CURRENT:
        return StrategyConfig(
            name="Current",
            strategy_type=StrategyType.CURRENT,
            rsi_buy_threshold=52.0,
            rsi_sell_threshold=48.0,
            macd_require_zero_cross=True,
            trend_confirmation_periods=1,
            indicators_required=3,  # All 3 must align
            use_volume_filter=False,
            description="Original strategy: All 3 indicators (trend + MACD + RSI) must align"
        )
    
    elif strategy_type == StrategyType.AGGRESSIVE:
        return StrategyConfig(
            name="Aggressive",
            strategy_type=StrategyType.AGGRESSIVE,
            rsi_buy_threshold=50.0,
            rsi_sell_threshold=50.0,
            macd_require_zero_cross=False,  # Any MACD cross
            trend_confirmation_periods=1,
            indicators_required=2,  # Any 2 of 3 indicators
            use_volume_filter=False,
            description="Aggressive strategy: Any 2 of 3 indicators must align, faster RSI crossover"
        )
    
    elif strategy_type == StrategyType.CONSERVATIVE:
        return StrategyConfig(
            name="Conservative",
            strategy_type=StrategyType.CONSERVATIVE,
            rsi_buy_threshold=55.0,
            rsi_sell_threshold=45.0,
            macd_require_zero_cross=True,
            trend_confirmation_periods=3,  # Require 3 consecutive periods
            indicators_required=3,  # All 3 must align
            use_volume_filter=True,
            volume_lookback_periods=20,
            description="Conservative strategy: All 3 indicators + volume confirmation + stronger trend"
        )
    
    else:
        raise ValueError(f"Unknown strategy type: {strategy_type}")


def get_all_strategies() -> list[StrategyConfig]:
    """Get all available strategy configurations."""
    return [
        get_strategy_config(StrategyType.CURRENT),
        get_strategy_config(StrategyType.AGGRESSIVE),
        get_strategy_config(StrategyType.CONSERVATIVE)
    ]