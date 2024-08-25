from dataclasses import dataclass
from enum import Enum
import itertools
import math
from typing import NamedTuple, Optional, Hashable, Union
import logging
import copy
import numpy as np
from game import Game, GameState

LOGGER = logging.getLogger(__name__)


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
# Lazily using a row and column of 0s to make the coords match the printed
# map coords without extra maths and off-by-one issues
TERRAIN = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 2, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0],
    [0, 2, 2, 2, 1, 5, 4, 0, 1, 0, 2, 2, 2, 3],
    [0, 2, 2, 3, 1, 1, 1, 5, 1, 1, 1, 2, 2, 2],
    [0, 0, 2, 3, 3, 2, 2, 1, 2, 5, 1, 2, 2, 2],
    [0, 0, 5, 4, 3, 3, 3, 2, 1, 1, 1, 1, 2, 2],
    [0, 0, 0, 2, 3, 3, 3, 2, 1, 1, 1, 1, 2, 2],
    [0, 0, 0, 3, 3, 3, 3, 2, 1, 1, 1, 1, 1, 0],
    [0, 0, 0, 2, 2, 3, 3, 2, 1, 1, 1, 1, 1, 0],
    [0, 0, 0, 0, 2, 2, 3, 2, 2, 4, 5, 1, 1, 0],
    [0, 0, 0, 0, 0, 2, 3, 2, 2, 2, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 2, 2, 2, 2, 2, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0],
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


class Feature(NamedTuple):
    """A feature on the board, e.g. a town or port"""

    feature_type: str
    location_name: Optional[str] = None
    revenue: Optional[list] = None


FEATURES = {
    (2, 5): Feature("PORT", "Burnie", [2, 2, 1, 1, 0, 0]),
    (2, 6): Feature("TOWN", "Ulverstone", [2, 2, 1, 1, 1, 1]),
    (7, 3): Feature("PORT", "Devonport", [3, 3, 1, 1, 0, 0]),
    (9, 4): Feature("PORT", "Launceston", [3, 3, 1, 1, 0, 0]),
    (3, 5): Feature("TOWN", "Queenstown", [2, 2, 2, 2, 2, 2]),
    (2, 5): Feature("PORT", "Port of Strahan", [2, 2, 0, 0, 0, 0]),
    (9, 9): Feature("TOWN", "New Norfolk", [2, 2, 2, 2, 2, 2]),
    (10, 9): Feature("PORT", "Hobart", [5, 5, 4, 4, 3, 3]),
    # TODO: Confirm water locations
    (8, 2): Feature("WATER1"),
    (8, 3): Feature("WATER1"),
    (8, 5): Feature("WATER2"),
    (9, 6): Feature("WATER1"),
    (3, 7): Feature("WATER2"),
    (4, 7): Feature("WATER1"),
    (6, 8): Feature("WATER1"),
    (6, 9): Feature("WATER1"),
    (10, 9): Feature("WATER1"),
    (5, 11): Feature("WATER2"),
    (9, 11): Feature("WATER2"),
    (6, 11): Feature("WATER1"),
}

PORTS = [c for c, f in FEATURES.items() if f.feature_type == "PORT"]


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
    Track((2, 4), None, True),
]


class CompanyDetails(NamedTuple):
    abb: str
    name: str
    starting: Optional[Coordinate]
    private: bool
    stock_available: int
    track_available: Optional[int]
    initial_treasury: int
    initial_interest: int


COMPANIES = {
    COMPANY.EBRC: CompanyDetails(
        "EB",
        "Emu Bay Railway Company",
        (3, 5),
        False,
        5,
        10,
        0,
        0,
    ),
    COMPANY.LW: CompanyDetails(
        "LW",
        "Launceston & Western",
        (9, 4),
        False,
        3,
        10,
        0,
        0,
    ),
    COMPANY.TMLC: CompanyDetails(
        "TMLC",
        "Tasmania Main Line",
        (9, 4),
        False,
        4,
        10,
        0,
        0,
    ),
    COMPANY.GT: CompanyDetails(
        "GT",
        "Grubbs Tramway",
        (2, 4),
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


def get_neighbors(x, y) -> list[Coordinate]:
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
        return [
            (x - 1, y - 1),
            (x, y - 1),
            (x + 1, y - 1),
            (x + 1, y),
            (x, y + 1),
            (x - 1, y),
        ]
    else:
        return [
            (x - 1, y),
            (x, y - 1),
            (x + 1, y),
            (x + 1, y + 1),
            (x, y + 1),
            (x - 1, y + 1),
        ]


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
    CHOOSE_BOND_CO = 4
    CHOOSE_BOND_CERT = 5
    CHOOSE_AUCTION = 6
    CHOOSE_MERGE_COS = 7
    CHOOSE_PRIVATE_HQ = 8
    CHOOSE_TRACK_CO = 9
    CHOOSE_TAKE_RESOURCE_CO = 10


class Action(Enum):
    BUILDING_TRACK = 0
    AUCTION_SHARE = 1
    TAKE_RESOURCES = 2
    ISSUE_BOND = 3
    MERGE = 4
    PAY_DIVIDEND = 5


ACTION_CUBE_SPACES = [
    Action.BUILDING_TRACK,
    Action.BUILDING_TRACK,
    Action.BUILDING_TRACK,
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
NO_MORE_BUILDS = (-1, -1)
BUILD_ACTIONS = 2


class Bond(NamedTuple):
    face_value: int
    interest: int


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
    company: COMPANY
    passed: list[Player]


class NormalTurnState(NamedTuple):
    action_removed: Optional[int] = None
    bond_co: Optional[int] = None
    company: Optional[COMPANY] = None
    operations: Optional[int] = 0  # Amount of builds or takes done so far


@dataclass
class CompanyState:
    treasury: int
    track_remaining: Optional[int]
    privates_owned: list[COMPANY]
    owned_by: Optional[COMPANY]
    shareholders: list[Player]
    interest: int = 0
    resources_to_sell: int = 0
    private_hq: Optional[Coordinate] = None


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
        phase_state: Union[AuctionState, NormalTurnState],
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
            assert isinstance(self.phase_state, NormalTurnState)
            return list(
                set(
                    [
                        ACTION_CUBE_SPACES[idx].value
                        for idx in range(len(self.action_cubes))
                        if not self.action_cubes[idx]
                        and not ACTION_CUBE_SPACES[idx].value
                        == self.phase_state.action_removed
                        and self.player_can_take_action(ACTION_CUBE_SPACES[idx])
                    ]
                )
            )
        if self.stage == InTurnStage.BUILDING_TRACK:
            # List of places the track can be placed
            # Also, cancel, if at least one move done
            pass
        if self.stage == InTurnStage.TAKE_RESOURCES:
            # List of resources available to companykk
            pass
        if self.stage == InTurnStage.CHOOSE_BOND_CO:
            # Company number 
            return [i.value for i in self.companies_owned(self.next_player)]
        if self.stage == InTurnStage.CHOOSE_BOND_CERT:
            # Index of bond remaining
            return [i for i, _ in enumerate(self.bonds_remaining)]
        if self.stage == InTurnStage.CHOOSE_AUCTION:
            # Company number if shares remaining
            pass
        if self.stage == InTurnStage.CHOOSE_MERGE_COS:
            # Index of share possibility
            pass
        if self.stage == InTurnStage.CHOOSE_PRIVATE_HQ:
            # X, Y of any forest or mountain
            pass
        if self.stage == InTurnStage.CHOOSE_TRACK_CO:
            # Company number owned, and can afford at least 1 track
            return [i.value for i in self.companies_owned(self.next_player)]
        if self.stage == InTurnStage.CHOOSE_TAKE_RESOURCE_CO:
            # Company number owned, if any resources can be taken
            return [i.value for i in self.companies_owned(self.next_player)]
            pass

        return []

    def current_player_can_take_action(self,  action: Action) -> bool:
        if action == Action.AUCTION_SHARE:
            return len(self.auctionable_companies()) > 0
        if action == Action.MERGE:
            return len(self.get_current_player_merge_options()) > 0
        if action == Action.TAKE_RESOURCES:
            return any([True for company in self.companies_owned(self.next_player) if self.resources_company_can_reach(company) > 0])
        if action == Action.BUILDING_TRACK:
            pass
        if action == Action.ISSUE_BOND:
            pass
        if action == Action.PAY_DIVIDEND:
            return True

    def companies_owned(self, player) -> list[COMPANY]:
        result: list[COMPANY] = []
        for company in COMPANY:
            if player in self.company_state[company].shareholders:
                result.append(company)
        return result

    def resources_company_can_reach(self, company): COMPANY -> list[Coordinate]:
        # TODO: This
        return []

    def auctionable_companies(self) -> list[COMPANY]:
        return [company for company in COMPANY if self.company_state[company].shareholders < COMPANIES[company].stock_available and self.company_state[company].owned_by is None]

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

    def shares_remaining(self, company) -> int:
        return COMPANIES[company].stock_available - len(
            self.company_state[company].shareholders
        )

    def get_current_player_merge_options(self) -> tuple[tuple[COMPANY, COMPANY], ...]:
        unmerged_privates = [
            company
            for company in COMPANY
            if self.company_state[company].owned_by is None
            and len(self.company_state[company].shareholders) > 0
            and COMPANIES[company].private
        ]
        publics = [company for company in COMPANY if not COMPANIES[company].private]
        merge_possibilities = itertools.product(publics, unmerged_privates)
        merge_options = (
            (company, private)
            for company, private in merge_possibilities
            if (
                self.last_player in self.company_state[company].shareholders
                or (self.last_player in self.company_state[private].shareholders)
            )
            and self.private_connected_to(company, private)
        )
        return tuple(merge_options)

    def private_connected_to(self, company, private) -> bool:
        # Check if the private is connected to any of the companies track
        private_hq = self.company_state[private].private_hq
        assert private_hq
        connected_track: list[Coordinate] = get_neighbors(*private_hq)
        visited_track = set([private_hq])
        while len(connected_track) > 0:
            track_coord = connected_track.pop()
            visited_track.add(track_coord)
            track = [t for t in self.track if t and t.location == track_coord]
            if any(t for t in track if t.owner == company):
                return True
            if any(t.narrow for t in track):
                connected_track.extend(
                    [i for i in get_neighbors(*track_coord) if i not in visited_track]
                )
        return False

    def get_track_cost(self, location: Coordinate, narrow: bool) -> int:
        tracks_at_location = [t for t in self.track if t and t.location == location]
        terrain_type = TERRAIN[location[0] + 1][location[1] + 1]
        feature_cost = sum(
            [
                FEATURE_COSTS.get(f.feature_type, 0)
                for l, f in FEATURES.items()
                if l == location
            ]
        )

        if not narrow:
            return (
                TERRAIN_COSTS[terrain_type]
                + feature_cost
                + TERRAIN_COSTS[terrain_type] * len(tracks_at_location)
            )
        else:
            return math.floor(TERRAIN_COSTS[terrain_type] / 2)

    def get_current_player_companies_held(self) -> list[COMPANY]:
        return [
            company
            for company in COMPANY
            if self.last_player in self.company_state[company].shareholders
        ]


class EbrGame(Game):
    def __init__(
        self, state: Optional[GameState] = None, player_count: int = 4
    ) -> None:
        if not (state):
            self.state = self.initialize_game(player_count)
        else:
            self.state = state.copy()

    def get_state(self) -> EbrGameState:
        return self.state

    def auction_action(self, bid):
        # action is bid
        # 0 is pass
        co = self.state.phase_state.company
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

        # Looks too complex - but if anybody has bidded and there is only one
        # player, or if nobody has bidded and everybody passed, then end auction
        if (self.state.phase_state.current_bid > 0 and len(still_in_auction) == 1) or (
            len(self.state.phase_state.passed) == self.state.player_count
        ):
            # End auction
            winner = self.state.phase_state.current_bidder
            self.state.company_state[co].shareholders.append(winner)
            self.state.company_state[co].treasury += self.state.phase_state.current_bid
            self.state.player_cash[winner] -= self.state.phase_state.current_bid
            if COMPANIES[co].private:
                self.expand_resources(co)
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
        current_in_order = IPO_ORDER.index(self.state.phase_state.company)
        if current_in_order == len(IPO_ORDER) - 1:
            # First player bought last co in ipo
            first_player = self.state.phase_state.current_bidder
            self.end_turn()
            self.state.next_player = first_player
        else:
            self.state.next_player = self.state.phase_state.current_bidder
            self.state.phase_state = AuctionState(
                self.state.next_player,
                0,
                IPO_ORDER[current_in_order + 1],
                [],
            )

    def expand_resources(self, co):
        coord = (
            self.state.company_state[co].private_hq[0],
            self.state.company_state[co].private_hq[1],
        )
        relevant = get_neighbors(*coord)
        relevant.append(coord)
        forest_neighbours = [
            tile for tile in relevant if TERRAIN[tile[1]][tile[0]] == FOREST
        ]
        mountain_neighbours = [
            tile for tile in relevant if TERRAIN[tile[1]][tile[0]] == MOUNTAIN
        ]
        for coord in forest_neighbours:
            self.state.resources.append(coord)
        for coord in mountain_neighbours:
            self.state.resources.append(coord)
            self.state.resources.append(coord)

    def game_action(self, action):
        if self.state.stage == InTurnStage.REMOVE_CUBES:
            self.remove_cube(action)
        elif self.state.stage == InTurnStage.TAKE_ACTION:
            self.take_action(action)
        elif self.state.stage == InTurnStage.CHOOSE_BOND_CO:
            self.choose_bond_co(action)
        elif self.state.stage == InTurnStage.CHOOSE_BOND_CERT:
            self.issue_bond(action)
        elif self.state.stage == InTurnStage.CHOOSE_MERGE_COS:
            self.choose_merge_cos(action)
        elif self.state.stage == InTurnStage.CHOOSE_AUCTION:
            self.start_auction(action)
        elif self.state.stage == InTurnStage.CHOOSE_PRIVATE_HQ:
            self.choose_private_hq(action)
        elif self.state.stage == InTurnStage.CHOOSE_TAKE_RESOURCE_CO:
            self.choose_take_resource_co(action)
        elif self.state.stage == InTurnStage.TAKE_RESOURCES:
            self.take_resources(action)
        elif self.state.stage == InTurnStage.CHOOSE_TRACK_CO:
            self.choose_track_co(action)
        elif self.state.stage == InTurnStage.BUILDING_TRACK:
            self.build_track(action)
        return

    def remove_cube(self, action):
        relevant_spaces = [
            i
            for i, space in enumerate(ACTION_CUBE_SPACES)
            if space.value == action and self.state.action_cubes[i]
        ]
        self.state.action_cubes[relevant_spaces[0]] = False
        self.state.stage = InTurnStage.TAKE_ACTION
        self.state.phase_state = NormalTurnState(action_removed=action)
        return

    def take_action(self, action):
        relevant_spaces = [
            i
            for i, space in enumerate(ACTION_CUBE_SPACES)
            if space.value == action and not self.state.action_cubes[i]
        ]
        self.state.action_cubes[relevant_spaces[0]] = True
        eff_action = Action(action)
        if eff_action == Action.ISSUE_BOND:
            self.state.stage = InTurnStage.CHOOSE_BOND_CO
        elif eff_action == Action.AUCTION_SHARE:
            self.state.stage = InTurnStage.CHOOSE_AUCTION
        elif eff_action == Action.PAY_DIVIDEND:
            self.pay_dividends()
        elif eff_action == Action.MERGE:
            self.state.stage = InTurnStage.CHOOSE_MERGE_COS
        elif eff_action == Action.TAKE_RESOURCES:
            self.state.stage = InTurnStage.CHOOSE_TAKE_RESOURCE_CO
        elif eff_action == Action.BUILDING_TRACK:
            self.state.stage = InTurnStage.CHOOSE_TRACK_CO

    def pay_dividends(self):
        self.state.last_dividend_was += 1
        for abbr, company in self.state.company_state.items():
            assert company
            if len(company.shareholders) == 0 or company.owned_by is not None:
                continue
            payout = 0
            if company.interest > 0:
                payout -= company.interest
            if company.resources_to_sell > 0:
                ports = self.get_ports_connected_to(abbr, company)
                payout += (1 + ports) * company.resources_to_sell
                company.resources_to_sell = 0
            for coord, feature in FEATURES.items():
                if feature.revenue:
                    # Todo - fix this, it ain't working - it's not returning the feature
                    has_track_in_location = [
                        track
                        for track in self.state.track
                        if track.location == coord and track.owner == abbr
                    ]
                    if len(has_track_in_location) > 0:
                        payout += feature.revenue[self.state.last_dividend_was]
            payout_per_shareholder = (
                math.ceil(payout / len(company.shareholders))
                if payout > 0
                else math.floor(payout / len(company.shareholders))
            )
            LOGGER.debug("%s Total payout: %d", abbr, payout)
            LOGGER.debug("%s Payout per shareholder: %d", abbr, payout_per_shareholder)
            # TODO: Implement cascading bankruptcy
            for shareholder in company.shareholders:
                self.state.player_cash[shareholder] += payout_per_shareholder

    def get_ports_connected_to(self, co_abbr: COMPANY, company_state: CompanyState):
        port_count = 0
        private_hqs_to_check: list[Coordinate] = []
        if not COMPANIES[co_abbr].private:
            pass
        else:
            if company_state.private_hq:
                private_hqs_to_check.append(company_state.private_hq)

        private_hqs_to_check.extend(
            [
                self.state.company_state[private].private_hq
                for private in company_state.privates_owned
                if self.state.company_state[private].private_hq
            ]
        )

        visited_track = set()
        for private_hq in private_hqs_to_check:
            visited_track.add(private_hq)
            connected_track: list[Coordinate] = get_neighbors(*private_hq)
            while len(connected_track) > 0:
                track_coord = connected_track.pop()
                visited_track.add(track_coord)
                track = [t for t in self.track if t and t.location == track_coord]
                # The Os. They're very big Os indeed. :s
                if any(t for t in track if t.narrow and t.location in PORTS):
                    port_count += 1
                if any(t.narrow for t in track):
                    connected_track.extend(
                        [
                            i
                            for i in get_neighbors(*track_coord)
                            if i not in visited_track
                        ]
                    )
        return port_count

    def choose_bond_co(self, action):
        self.state.phase_state = NormalTurnState(company=COMPANY(action))
        self.state.stage = InTurnStage.CHOOSE_BOND_CERT
        pass

    def issue_bond(self, action):
        bond = self.state.bonds_remaining[action]
        self.state.bonds_remaining.remove(bond)
        assert isinstance(self.state.phase_state, NormalTurnState)
        assert self.state.phase_state.company is not None
        company = self.state.company_state[self.state.phase_state.company]
        company.treasury += bond.face_value
        company.interest += bond.interest
        self.end_turn()

    def choose_merge_cos(self, action):
        merge_options = self.state.get_current_player_merge_options()
        co_idx, private_idx = merge_options[action]
        company = self.state.company_state[co_idx]
        private = self.state.company_state[private_idx]
        company.privates_owned.append(private_idx)
        private.owned_by = co_idx
        company.shareholders.append(private.shareholders[0])
        private.shareholders = []
        company.interest += private.interest
        private.interest = 0
        company.treasury += private.treasury
        private.treasury = 0
        self.end_turn()

    def choose_take_resource_co(self, action):
        self.state.phase_state = NormalTurnState(company=COMPANY(action))
        self.state.stage = InTurnStage.TAKE_RESOURCES

    def take_resources(self, action):
        self.state.company_state[self.state.phase_state.company].resources_to_sell += 1
        self.state.resources.remove(Coordinate(action))
        self.end_turn()

    def choose_track_co(self, action):
        self.state.phase_state = NormalTurnState(company=COMPANY(action), operations=0)
        self.state.stage = InTurnStage.BUILDING_TRACK

    def build_track(self, action):
        # This is hacky
        if action == NO_MORE_BUILDS:
            self.end_turn()
            return

        company = self.state.company_state[self.state.phase_state.company]
        coord = Coordinate(action)
        assert isinstance(self.state.phase_state, NormalTurnState)
        if COMPANIES[self.state.phase_state.company].private:
            self.state.private_track_remaining -= 1
            self.state.track.append(Track(coord, None, True))
            track_cost = self.state.get_track_cost(coord, True)
            if company.owned_by:
                self.state.company_state[company.owned_by].treasury -= track_cost
            else:
                company.treasury -= track_cost
        else:
            company.track_remaining -= 1
            self.state.track.append(Track(coord, self.state.phase_state.company, False))
            track_cost = self.state.get_track_cost(coord, False)
            company.treasury -= track_cost
        self.state.phase_state = NormalTurnState(
            company=self.state.phase_state.company,
            operations=self.state.phase_state.operations + 1,
        )

        if self.state.phase_state.operations >= BUILD_ACTIONS:
            self.end_turn()

    def start_auction(self, action):
        company = COMPANY(action)
        if COMPANIES[company].private:
            self.state.stage = InTurnStage.CHOOSE_PRIVATE_HQ
            self.state.phase_state = NormalTurnState(company=company)
        else:
            self.state.phase = Phase.AUCTION
            self.state.phase_state = AuctionState(
                self.state.last_player, 0, company, []
            )

    def choose_private_hq(self, action):
        self.state.company_state[self.state.phase_state.company].private_hq = (
            Coordinate(action)
        )
        self.state.phase = Phase.AUCTION
        self.state.phase_state = AuctionState(
            self.state.last_player, 0, self.state.phase_state.company, []
        )

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
                private_hq=company.starting,
                interest=company.initial_interest,
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
        if FEATURES[(x, y)].feature_type == "WATER1":
            return "" + base_symbol + "\033[34m~"
        if FEATURES[(x, y)].feature_type == "WATER2":
            return "" + base_symbol + "\033[34m≈"
        return "" + base_symbol + "O"
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
    print("     " + "  ".join([f"{x:2}" for x in range(1, 13)]))
    for y, row in enumerate(board):
        upper_row = [
            "   "
            + get_track_symbol(x, y, game)
            + get_symbol(x, y, row[x])
            + get_resource_symbol(x, y, game)
            for x in range(1, len(row), 2)
        ]
        lower_row = [
            "   "
            + get_track_symbol(x, y, game)
            + get_symbol(x, y, row[x])
            + get_resource_symbol(x, y, game)
            for x in range(2, len(row), 2)
        ]
        print(f"{y :2}" + "".join(upper_row))
        print(f"{y :2}    " + "".join(lower_row))
    print("\033[0m")
