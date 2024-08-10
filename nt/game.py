from hashlib import sha256
import typing
import numpy as np
from game.game import Game
from game.game_state import GameState

# Basic implementation of a game that might be similar to no-thanks

# Hard coding for now
PLAYER_COUNT = 5

ACTION_NO_THANKS = 1
ACTION_TAKE = 2


class NtState(GameState):
    def __init__(
        self, next_player_id, last_player_id, previous_actions, next_automated=False
    ):
        # Technically, only cards 3 to 35 are there - but memory
        # cost is worth it
        self.next_player_id = next_player_id
        self.last_player_id = last_player_id
        self.cards = np.zeros(36)
        self.cards[0] = -1
        self.cards[1] = -1
        self.cards[2] = -1
        self.card_on_board = None
        self.chips = np.zeros(PLAYER_COUNT)
        self.chips_on_board = 0
        self._winner = -1
        self._previous_actions = previous_actions.copy()
        self._next_automated = next_automated

    @property
    def player_id(self):
        return self.last_player_id

    @property
    def next_automated(self):
        return self._next_automated

    @next_automated.setter
    def next_automated(self, value):
        self._next_automated = value

    @property
    def permitted_actions(self):
        if self.card_on_board is None:
            # About to draw cards
            return [(action,) for action in np.where(self.cards == 0)[0]]
        if self.chips[self.next_player_id] == 0:
            return [ACTION_TAKE]
        else:
            return [ACTION_NO_THANKS, ACTION_TAKE]

    @property
    def winner(self):
        return self._winner

    @property
    def previous_actions(self):
        return self._previous_actions

    def add_action(self, action):
        self._previous_actions.append(action)

    def hash(self):
        return sha256(str(self).encode()).hexdigest()

    def cards_remaining(self):
        # Cards 3-35
        # 9 cards removed
        return (35 - np.count_nonzero(self.cards)) - 11

    def copy(self) -> "NtState":

        copy_state = NtState(
            self.next_player_id,
            self.last_player_id,
            self.previous_actions,
            self.next_automated,
        )
        copy_state.cards = self.cards.copy()
        copy_state.card_on_board = self.card_on_board
        copy_state.chips = self.chips.copy()
        copy_state.chips_on_board = self.chips_on_board
        copy_state._winner = self._winner
        return copy_state


class NtGame(Game):
    @classmethod
    def from_state(cls, state: GameState) -> "NtGame":
        return cls(typing.cast("NtState", state))

    @classmethod
    def max_action_count(cls) -> int:
        # 2 actual actions
        # And 35 cards for auto-actions
        # (and 1 extra - index is the card number for coding simplicity)
        return 36

    @property
    def state(self) -> "NtState":
        return self._state

    def __init__(self, state: typing.Optional["NtState"] = None) -> None:
        if state:
            self._state = state
        else:
            self._state = self.initialize_game()

        self.player_count = PLAYER_COUNT

    def initialize_game(self) -> "NtState":
        self._state = NtState(0, 0, [], True)
        self._state.chips = np.full(PLAYER_COUNT, 11)

        return self._state

    def act(self, action: int) -> "NtState":
        self._state.last_player_id = self._state.next_player_id
        self._state.add_action(action)
        if action == ACTION_NO_THANKS:
            self._state.chips[self._state.player_id] -= 1
            self._state.chips_on_board += 1
            self._state.next_player_id = (self._state.player_id + 1) % PLAYER_COUNT
            self._state.next_automated = False
            # Not checking for invalid
        elif action == ACTION_TAKE:
            self._state.next_automated = True
            self._state.chips[self._state.player_id] += self._state.chips_on_board
            self._state.cards[self._state.card_on_board] = self._state.player_id + 1
            self._state.card_on_board = None
            self._state.chips_on_board = 0
            if self._state.cards_remaining() == 0:
                scores = np.array([self.score_player(i) for i in range(PLAYER_COUNT)])
                self._state._winner = np.argmax(scores)
        elif action == 255:
            # First action in the game
            pass
        else:
            raise ValueError("Invalid action")
        return self._state

    def non_player_act(self) -> tuple[tuple[int, ...], "NtState"]:
        if self._state.card_on_board is not None:
            return tuple(), self._state

        # Draw card
        card = np.random.choice(np.where(self._state.cards == 0)[0])
        self.apply_non_player_acts((card,))
        return ((card,), self._state)

    def apply_non_player_acts(self, actions: tuple[int, ...]) -> "NtState":
        assert len(actions) == 1
        assert self._state.next_automated
        self._state.next_automated = False
        self._state.card_on_board = actions[0]
        assert isinstance(actions, tuple)
        self._state.add_action(actions)
        return self._state

    def score_player(self, player_id: int) -> int:
        cards_held = np.sort(np.where(self._state.cards == player_id + 1))[0]
        score = 0
        last_card = None
        for card in cards_held:
            if last_card != (card - 1):
                score += card
            last_card = card
        score -= self._state.chips[player_id]

        return score
