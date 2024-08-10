def human_play(game, tree):
    done = False
    game.debug_print()
    while not done:
        print("--------")
        print("01234567")
        if game.state.next_player_id == 0:
            action = None
            while action == None:
                try:
                    proposed_action = int(input("Enter your action: "))
                    if (proposed_action) in game.state.permitted_actions:
                        action = int(proposed_action)
                    else:
                        print("✖️")
                except ValueError:
                    print("✖️")
        else:
            action = tree.act(game.state)
        next_state = game.act(action)
        state = next_state
        game.debug_print()
        done = next_state.winner != -1
    tree.to_disk()
