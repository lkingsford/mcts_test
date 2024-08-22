from ebr.game import *


def print_holdings(game_state: EbrGameState):
    for player in range(game_state.player_count):
        holding_string = f"{player}: £{game_state.player_cash[player]}"
        for company in game_state.company_state.items():
            holding_string += (" " + company[0].name) * company[1].shareholders.count(
                player
            )
        print(holding_string)


def human_play(game: EbrGame, tree):
    done = False
    print_terrain(TERRAIN, game)
    while not done:
        print("--------")
        # Check for which player here
        action = None
        while action == None:
            if (
                game.state.phase == Phase.AUCTION
                or game.state.phase == Phase.INITIAL_AUCTION
            ):
                print_holdings(game.state)
                print(
                    f"Bid for {game.state.phase_state.company_for_auction.name}: {game.state.phase_state.current_bid} ({game.state.phase_state.current_bidder})"
                )
                bid = input(
                    f"Player {game.state.next_player} (£{game.state.player_cash[game.state.next_player]}): "
                )
                if int(bid) in game.state.permitted_actions:
                    action = int(bid)
            else:
                pass
        game.act(action)
