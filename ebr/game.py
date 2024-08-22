from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple, Optional, Hashable
import numpy as np
import copy
from game import Game, GameState

# LET'S WRITE PYTHON LIKE WE'RE USING C STRUCTS!
# I don't really like this, but we are strictly separating state from logic,
# and it's a model that makes sense from that POV.
# I might think of better ways to do this - but this is a tool for me - and it
# matters primarily that I understand it, and am writing it in a relatively
# brief amount of time.


Coordinate = tuple[int, int]
Player = int

FINAL_DIVIDEND_COUNT = 6

NOTHING = 0
PLAIN = 1
FOREST = 2
MOUNTAIN = 3
TOWN = 4
PORT = 5

# Not using the consts, because easier to read with the consisitent width cells
TERRAIN = [
    [1, 2, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0],
    [2, 2, 2, 1, 5, 4, 0, 1, 0, 2, 2, 2, 3],
    [2, 2, 3, 1, 1, 1, 5, 1, 1, 1, 2, 2, 2],
    [0, 2, 3, 3, 2, 2, 1, 2, 5, 1, 2, 2, 2],
    [0, 5, 4, 3, 3, 3, 2, 1, 1, 1, 1, 2, 2],
    [0, 0, 2, 3, 3, 3, 2, 1, 1, 1, 1, 2, 2],
    [0, 0, 3, 3, 3, 3, 2, 1, 1, 1, 1, 1, 0],
    [0, 0, 2, 2, 3, 3, 2, 1, 1, 1, 1, 1, 0],
    [0, 0, 0, 2, 2, 3, 2, 2, 4, 5, 1, 1, 0],
    [0, 0, 0, 0, 2, 3, 2, 2, 2, 0, 0, 0, 0],
    [0, 0, 0, 0, 2, 2, 2, 2, 2, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0],
]

SYMBOL = {
    0: " ",
    1: "\033[37m-",
    2: "\033[32m=",
    3: "\033[32m^",
    4: "\033[33mT",
    5: "\033[31mP",
}

TERRAIN_COSTS = {PLAIN: 3, FOREST: 4, MOUNTAIN: 6, TOWN: 4, PORT: 5}

FEATURE_COSTS = {"WATER1": 1, "WATER2": 3}

MULTIPLE_TRACK_ALLOWED = {
    PLAIN: True,
    FOREST: False,
    MOUNTAIN: False,
    TOWN: True,
    PORT: True,
}

FEATURES = {
    (5, 2): ("PORT", "Burnie", [2, 2, 1, 1, 0, 0]),
    (6, 2): ("TOWN", "Ulverstone", [2, 2, 1, 1, 1, 1]),
    (3, 7): ("PORT", "Devonport", [3, 3, 1, 1, 0, 0]),
    (4, 9): ("PORT", "Launceston", [3, 3, 1, 1, 0, 0]),
    (5, 3): ("TOWN", "Queenstown", [2, 2, 2, 2, 2, 2]),
    (5, 2): ("PORT", "Port of Strahan", [2, 2, 0, 0, 0, 0]),
    (9, 9): ("TOWN", "New Norfolk", [2, 2, 2, 2, 2, 2]),
    (9, 10): ("PORT", "Hobart", [5, 5, 4, 4, 3, 3]),
    (8, 2): ("WATER1",),
    (8, 3): ("WATER1",),
    (8, 5): ("WATER2",),
    (9, 6): ("WATER1",),
    (3, 7): ("WATER2",),
    (4, 7): ("WATER1",),
    (6, 8): ("WATER1",),
    (6, 9): ("WATER1",),
    (10, 9): ("WATER1",),
    (5, 11): ("WATER2",),
    (9, 11): ("WATER2",),
    (6, 11): ("WATER1",),
}


class COMPANY(Enum):
    EBRC = 0
    LW = 1
    TMLC = 2
    GT = 3
    NMFT = 4
    NED = 5
    MLM = 6


IPO_ORDER = [COMPANY.LW, COMPANY.TMLC, COMPANY.EBRC, COMPANY.GT]


class Track(NamedTuple):
    location: Coordinate
    owner: Optional[COMPANY]
    narrow: bool = False


INITIAL_TRACK = [
    Track((9, 4), COMPANY.LW),
    Track((9, 4), COMPANY.TMLC),
    Track((3, 5), COMPANY.EBRC),
]


class CompanyDetails(NamedTuple):
    abb: str
    name: str
    starting: Optional[Coordinate]
    private: bool
    stock_available: int
    track_available: Optional[int]
    initial_treasury: int
    initial_repayment: int


COMPANIES = {
    COMPANY.EBRC: CompanyDetails(
        "EB",
        "Emu Bay Railway Company",
        (5, 3),
        False,
        5,
        10,
        0,
        0,
    ),
    COMPANY.LW: CompanyDetails(
        "LW",
        "Launceston & Western",
        (4, 9),
        False,
        3,
        10,
        0,
        0,
    ),
    COMPANY.TMLC: CompanyDetails(
        "TMLC",
        "Tasmania Main Line",
        (4, 9),
        False,
        4,
        10,
        0,
        0,
    ),
    COMPANY.GT: CompanyDetails(
        "GT",
        "Grubbs Tramway",
        None,
        True,
        1,
        None,
        10,
        2,
    ),
    COMPANY.NMFT: CompanyDetails(
        "NMFT",
        "North Mount Farrell Tramway",
        None,
        True,
        1,
        None,
        0,
        0,
    ),
    COMPANY.NED: CompanyDetails(
        "NED",
        "North East Dundas",
        None,
        True,
        1,
        None,
        15,
        3,
    ),
    COMPANY.MLM: CompanyDetails(
        "MLM",
        "Mount Lyell Mining & Railway Company",
        None,
        True,
        1,
        None,
        20,
        5,
    ),
}


def get_neighbors(x, y) -> list[tuple]:
    # Game is a hex map with pointy sides
    # Each row is top, bottom, top, bottom
    #
    # 1,1        3, 1       5,1
    #      2,1        4, 1
    # 1,2        3, 2,      5,2
    #      2,2        4, 2
    # 1,3        3, 3       5,3
    #      2,3        4, 3
    # This doesn't take into account the map

    if y % 2 == 1:
        return [(x - 1, y - 1), (x, y - 1), (x + 1, y - 1), (x + 1, y), (x - 1, y)]
    else:
        return [(x - 1, y), (x + 1, y), (x + 1, y + 1), (x, y + 1), (x - 1, y + 1)]


class Phase(Enum):
    INITIAL_AUCTION = 0
    NORMAL_TURN = 1
    AUCTION = 2


class EndGameReason(Enum):
    SHARES = 0
    BONDS = 1
    TRACK = 2
    RESOURCE = 3


class InTurnStage(Enum):
    REMOVE_CUBES = 0
    TAKE_ACTION = 1
    BUILDING_TRACK = 2
    TAKE_RESOURCES = 3


class Action(Enum):
    BUILD_TRACK = 0
    AUCTION_SHARE = 1
    TAKE_RESOURCES = 2
    ISSUE_BOND = 3
    MERGE = 4
    PAY_DIVIDEND = 5


ACTION_CUBE_SPACES = [
    Action.BUILD_TRACK,
    Action.BUILD_TRACK,
    Action.BUILD_TRACK,
    Action.AUCTION_SHARE,
    Action.AUCTION_SHARE,
    Action.TAKE_RESOURCES,
    Action.TAKE_RESOURCES,
    Action.TAKE_RESOURCES,
    Action.ISSUE_BOND,
    Action.MERGE,
    Action.PAY_DIVIDEND,
]

ACTION_CUBE_STARTING_SPACE_IDXS = [5, 6, 7, 10]


class Bond(NamedTuple):
    face_value: int
    coupon: int


BONDS = [
    Bond(5, 1),
    Bond(5, 1),
    Bond(10, 3),
    Bond(10, 3),
    Bond(10, 4),
    Bond(15, 4),
    Bond(15, 5),
]

# Cash for each player count
INITIAL_CASH = {
    2: 20,
    3: 13,
    4: 10,
    5: 8,
}


class AuctionState(NamedTuple):
    current_bidder: Player
    current_bid: int
    company_for_auction: COMPANY
    passed: list[Player]


@dataclass
class CompanyState:
    treasury: int
    track_remaining: Optional[int]
    privates_owned: list[COMPANY]
    owned_by: Optional[COMPANY]
    shareholders: list[Player]
    # need to add rev and debt (coupons)


class EbrGameState(GameState):
    def __init__(
        self,
        player_count: int,  # Should this be here? Identical over tree, but relevant if saved
        last_player: Player,
        next_player: Player,
        active_player: Player,
        # Active player is the player whose turn it actually is - last/next_player are
        # who is doing something (like bidding in an auction), but active_player is
        # whose turn it currently is (so, who might have started the auction)
        action_cubes: list[bool],
        player_cash: list[int],
        phase: Phase,
        stage: Optional[InTurnStage],
        last_dividend_was: int,
        end_game_trigger_states: dict[EndGameReason, bool],
        phase_state: AuctionState,
        track: list[Track],
        resources: list[Coordinate],
        private_track_remaining: int,
        company_state: dict[COMPANY, CompanyState],
        bonds_remaining: list[Bond],
        previous_actions: list[int],
    ) -> None:
        super().__init__()
        self._player_count = player_count
        self.last_player = last_player
        self.next_player = next_player
        self.action_cubes = copy.deepcopy(action_cubes)
        self.last_dividend_was = last_dividend_was
        self.end_game_trigger_states = copy.deepcopy(end_game_trigger_states)
        self.phase = phase
        self.stage = stage
        self.phase_state = phase_state
        self.track = copy.deepcopy(track)
        self.private_track_remaining = private_track_remaining
        self.resources = copy.deepcopy(resources)
        self.private_track_remaining = private_track_remaining
        self.company_state = copy.deepcopy(company_state)
        self.bonds_remaining = copy.deepcopy(bonds_remaining)
        self.player_cash = copy.deepcopy(player_cash)
        self.active_player = active_player
        self._previous_actions = previous_actions

    @property
    def player_id(self) -> int:
        return self.last_player
        pass

    @property
    def permitted_actions(self) -> list[int]:
        if self.phase == Phase.INITIAL_AUCTION or self.phase == Phase.AUCTION:
            return [0] + list(
                range(
                    self.phase_state.current_bid + 1,
                    self.player_cash[self.next_player] + 1,
                )
            )
        if self.stage == InTurnStage.REMOVE_CUBES:
            return list(
                set(
                    [
                        ACTION_CUBE_SPACES[idx].value
                        for idx in range(len(self.action_cubes))
                        if self.action_cubes[idx]
                    ]
                )
            )
        if self.stage == InTurnStage.TAKE_ACTION:
            return list(
                set(
                    [
                        ACTION_CUBE_SPACES[idx].value
                        for idx in range(len(self.action_cubes))
                        if not self.action_cubes[idx]
                    ]
                )
            )

        return []

    def winner(self) -> int:
        pass

    @property
    def player_count(self) -> int:
        return self._player_count

    def loggable(self) -> dict:
        pass

    @property
    def previous_actions(self) -> list[int]:
        return self._previous_actions


class EbrGame(Game):
    def __init__(
        self, state: Optional[GameState] = None, player_count: int = 4
    ) -> None:
        if not (state):
            self.state = self.initialize_game(player_count)
        else:
            self.state = state.copy()

    def valid_actions(self, state):
        return []

    def get_state(self) -> EbrGameState:
        return self.state

    def auction_action(self, bid):
        # action is bid
        # 0 is pass
        co = self.state.phase_state.company_for_auction
        if bid > self.state.phase_state.current_bid:
            self.state.phase_state = AuctionState(
                self.state.last_player,
                bid,
                co,
                self.state.phase_state.passed,
            )
        else:
            passed = self.state.phase_state.passed
            passed.append(self.state.last_player)
            self.state.phase_state = AuctionState(
                self.state.phase_state.current_bidder,
                self.state.phase_state.current_bid,
                co,
                passed,
            )

        still_in_auction = [
            player
            for player in range(self.state.player_count)
            if player not in self.state.phase_state.passed
            and self.state.player_cash[player] > bid
        ]

        if len(still_in_auction) == 1:
            # End auction
            self.state.company_state[co].shareholders.append(still_in_auction[0])
            self.state.company_state[co].treasury += self.state.phase_state.current_bid
            self.state.player_cash[
                self.state.phase_state.current_bidder
            ] -= self.state.phase_state.current_bid
            if self.state.phase == Phase.AUCTION:
                self.end_turn()
            else:
                # IPO
                self.next_ipo()
        else:
            next_bidder = (self.state.last_player + 1) % self.state.player_count
            while next_bidder in self.state.phase_state.passed:
                next_bidder = (next_bidder + 1) % self.state.player_count
            self.state.next_player = next_bidder

    def next_ipo(self):
        current_in_order = IPO_ORDER.index(self.state.phase_state.company_for_auction)
        if current_in_order == len(IPO_ORDER) - 1:
            # First player bought last co in ipo
            first_player = self.state.phase_state.current_bidder
            self.end_turn()
            self.active_player = first_player
        else:
            self.state.next_player = self.state.phase_state.current_bidder
            self.state.phase_state = AuctionState(
                self.state.next_player,
                0,
                IPO_ORDER[current_in_order + 1],
                [],
            )

    def game_action(self, action):
        if self.state.stage == InTurnStage.REMOVE_CUBES:
            relevant_spaces = [
                i
                for i, space in enumerate(ACTION_CUBE_SPACES)
                if space.value == action and self.state.action_cubes[i]
            ]
            self.state.action_cubes[relevant_spaces[0]] = False
            self.state.stage = InTurnStage.TAKE_ACTION
            return

        if self.state.stage == InTurnStage.TAKE_ACTION:
            relevant_spaces = [
                i
                for i, space in enumerate(ACTION_CUBE_SPACES)
                if space.value == action and not self.state.action_cubes[i]
            ]
            self.state.action_cubes[relevant_spaces[0]] = True
            return

    def max_action_count(cls) -> int:
        return 255

    def from_state(cls, state: GameState) -> "Game":
        # Separate to allow abstract method to work
        assert isinstance(state, EbrGameState)
        return cls(state)

    def end_turn(self):
        self.state.next_player = (
            self.state.active_player + 1
        ) % self.state.player_count
        self.state.active_player = self.state.next_player
        self.state.phase_state = None
        self.state.phase = Phase.NORMAL_TURN
        self.state.stage = InTurnStage.REMOVE_CUBES
        self.winner = self.update_end_game()

    def update_end_game(self):
        return -1

    def act(self, action) -> GameState:
        self.state.last_player = self.state.next_player
        if (
            self.state.phase == Phase.INITIAL_AUCTION
            or self.state.phase == Phase.AUCTION
        ):
            self.auction_action(action)
        else:
            self.game_action(action)
        return self.state

    def is_game_over(self, state: GameState) -> bool:
        return False

    def initialize_game(self, player_count) -> EbrGameState:
        end_game_trigger_states = {reason: False for reason in EndGameReason}
        action_cubes = [False] * len(ACTION_CUBE_SPACES)

        for location in ACTION_CUBE_STARTING_SPACE_IDXS:
            action_cubes[location] = True

        last_dividend = 0

        track = INITIAL_TRACK
        player_cash = [INITIAL_CASH[player_count]] * player_count

        company_state = {
            key: CompanyState(
                treasury=company.initial_treasury,
                track_remaining=company.track_available,
                privates_owned=[],
                owned_by=None,
                shareholders=[],
            )
            for key, company in COMPANIES.items()
        }

        phase = Phase.INITIAL_AUCTION
        auction_state = AuctionState(0, 0, COMPANY.LW, [])

        last_player = 0
        next_player = auction_state.current_bidder

        bonds_remaining = copy.deepcopy(BONDS)
        resources: list[Coordinate] = []
        previous_actions = [255]
        return EbrGameState(
            player_count=player_count,
            last_player=last_player,
            next_player=next_player,
            active_player=last_player,
            action_cubes=action_cubes,
            player_cash=player_cash,
            phase=phase,
            stage=None,
            last_dividend_was=last_dividend,
            end_game_trigger_states=end_game_trigger_states,
            phase_state=auction_state,
            track=track,
            resources=resources,
            private_track_remaining=0,
            company_state=company_state,
            bonds_remaining=bonds_remaining,
            previous_actions=previous_actions,
        )


def get_symbol(x, y, terrain):
    base_symbol = SYMBOL[terrain]
    if (x, y) in FEATURES:
        if FEATURES[(x, y)][0] == "WATER1":
            return "" + base_symbol + "\033[34m~"
        if FEATURES[(x, y)][0] == "WATER2":
            return "" + base_symbol + "\033[34m≈"
    return "" + base_symbol + " "


def get_track_symbol(x, y, game):
    track = [t for t in game.state.track if t and t.location == (x, y)]
    eb = any([t.owner == COMPANY.EBRC for t in track])
    lw = any([t.owner == COMPANY.LW for t in track])
    tmlc = any([t.owner == COMPANY.TMLC for t in track])
    narrow = any([t.narrow for t in track])
    symbol = eb + 2 * lw + 4 * tmlc + 8 * narrow
    return "\033[0m" + str(symbol) if symbol else " "


def get_resource_symbol(x, y, game):
    resources = len([1 for r in game.state.resources if r == (x, y)])
    return f"\033[35m{resources}" if resources else " "


# Terrain is staggered - a row looks like
# 0   2   4
#   1   3   5
def print_terrain(board, game: EbrGame):
    print("   " + " ".join([f"{x:2}" for x in range(13)]))
    for y, row in enumerate(board):
        upper_row = [
            "   "
            + get_track_symbol(x, y + 1, game)
            + get_symbol(x, y + 1, row[x - 1])
            + get_resource_symbol(x, y, game)
            for x in range(1, len(row), 2)
        ]
        lower_row = [
            "   "
            + get_track_symbol(x, y + 1, game)
            + get_symbol(x, y + 1, row[x - 1])
            + get_resource_symbol(x, y, game)
            for x in range(2, len(row), 2)
        ]
        print(f"{y + 1:2}" + "".join(upper_row))
        print(f"{y + 1:2}    " + "".join(lower_row))
    print("\033[0m")
