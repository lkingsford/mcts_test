import nt.game


def human_play(game: nt.game.NtGame, tree):
    done = False
    state = game.initialize_game()
    while not done:
        _actions, state = game.non_player_act()
        print("--------")
        for player in range(game.player_count):
            player_cards = [
                "   " if owner != player + 1 else f"{card_no:2d} "
                for card_no, owner in enumerate(state.cards)
            ]
            player_cards_str = "".join(player_cards)
            player_info = (
                str(player)
                + " "
                + player_cards_str
                + " - "
                + str(state.chips[player])
                + " chips"
            )
            print(player_info)
        print("")
        print(
            f"Current Card: {state.card_on_board} ({state.chips_on_board} chips) - {state.cards_remaining()} cards remaining"
        )
        must_take = state.chips[state.player_id] == 0
        action = None
        if must_take:
            print("Must Take")
            action = nt.game.ACTION_TAKE
        else:
            while action == None:
                proposed_action_raw = input("(N)o Thanks or (T)ake:")
                proposed_action_cleaned = proposed_action_raw.strip().upper()
                if proposed_action_cleaned == "N" or "":
                    action = nt.game.ACTION_NO_THANKS
                elif proposed_action_cleaned == "T":
                    action = nt.game.ACTION_TAKE
                else:
                    print("✖️")

        assert action
        state = game.act(action)
        done = state.winner != -1

    print("Scores")
    for player in range(game.player_count):
        print(f"Player {player}: {game.score_player(player)}")
    # tree.to_disk()
