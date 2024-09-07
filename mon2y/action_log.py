from enum import Enum
import json
import os
from datetime import datetime
from typing import Optional, NamedTuple

import numpy as np

from .state import State
from .node import Action


class ActionLog(NamedTuple):
    action: Action
    player_id: Optional[int]
    state: State
    memo: Optional[dict]


class ActionLogEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, int):
            return obj
        if isinstance(obj, tuple):
            return tuple(self.default(e) for e in obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, Enum):
            return str(obj)
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, ActionLog):
            return {
                "action": super(ActionLogEncoder, self).default(obj.action),
                "player_id": obj.player_id,
                "state": obj.state,
                "memo": super(ActionLogEncoder, self).default(obj.memo),
            }
        return super(ActionLogEncoder, self).default(obj)


def save_report(folder, actions: list[ActionLog]):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, f"{datetime.now()}.json"), "w") as f:
        json.dump(actions, f, cls=ActionLogEncoder)
