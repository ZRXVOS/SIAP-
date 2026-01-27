"""
GemaScreener Rules Module
Berisi 7 rumus screening saham (Rule 1-7)
"""

from .rule1_konsisten import check_rule1, RULE1_NAME, RULE1_DESCRIPTION
from .rule2_breakout import check_rule2, RULE2_NAME, RULE2_DESCRIPTION
from .rule3_reversal import check_rule3, RULE3_NAME, RULE3_DESCRIPTION
from .rule4_rsi2_mean_reversion import check_rule4
from .rule5_dual_ma_crossover import check_rule5
from .rule6_bollinger_mean_reversion import check_rule6
from .rule7_breakout_volume import check_rule7

# Rule names untuk rules 4-7
RULE4_NAME = "RSI-2 Mean Reversion"
RULE5_NAME = "Dual MA Crossover"
RULE6_NAME = "Bollinger Mean Reversion"
RULE7_NAME = "Breakout Volume"

__all__ = [
    'check_rule1', 'RULE1_NAME', 'RULE1_DESCRIPTION',
    'check_rule2', 'RULE2_NAME', 'RULE2_DESCRIPTION',
    'check_rule3', 'RULE3_NAME', 'RULE3_DESCRIPTION',
    'check_rule4', 'RULE4_NAME',
    'check_rule5', 'RULE5_NAME',
    'check_rule6', 'RULE6_NAME',
    'check_rule7', 'RULE7_NAME',
]
