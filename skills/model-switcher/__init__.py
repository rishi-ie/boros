"""
model_switcher skill — runtime model selection for Boros.

Allows switching the evolution/meta_eval/eval_generator providers on the fly
without restart. Stores current config in session/active_model.json.
"""

# Functions exposed by this skill:
# - model_switch_get: returns current model config
# - model_switch_set: switches to a different model/provider
# - model_switch_list: lists available models from config
# - model_switch_update_config: updates config.json providers

from .functions.model_switch_get import model_switch_get
from .functions.model_switch_set import model_switch_set
from .functions.model_switch_list import model_switch_list
from .functions.model_switch_update_config import model_switch_update_config