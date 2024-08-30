from ebr.game import *
from mcts.tree import Tree


def print_holdings(game_state: EbrGameState):
    for player in range(game_state.player_count):
        holding_string = f"{player}: £{game_state.player_cash[player]}"
        for company in game_state.company_state.items():
            holding_string += (" " + company[0].name) * company[1].shareholders.count(
                player
            )
        print(holding_string)


def print_cube_display(game_state: EbrGameState):
    for i, cube in enumerate(game_state.action_cubes):
        print(
            f"{ACTION_CUBE_SPACES[i].value}: {ACTION_CUBE_SPACES[i].name} "
            + ("[#]" if cube else "[ ]")
        )


def print_companies(game_state: EbrGameState):
    for i, company in enumerate(game_state.company_state.items()):
        print(f"{i}: {company}")


def tree_input(prompt: str, tree: Tree, game_state: EbrGameState) -> str:
    """
    Custom input function that accepts a prompt and a tree.

    If the input is 'a', return result of tree.act for the input instead of the input.
    """
    while True:
        user_input = input(prompt)
        if user_input == "a":
            action = tree.act(game_state)
            if isinstance(action, tuple):
                return ",".join(str(x) for x in action)
            else:
                return str(action)
        else:
            return user_input


def human_play(game: EbrGame, tree: Tree):
    done = False
    while not done:
        print("--------")
        # Check for which player here
        action = None
        while action == None:
            print(f"Permitted actions: {game.state.permitted_actions}")
            print_holdings(game.state)
            if (
                game.state.phase == Phase.AUCTION
                or game.state.phase == Phase.INITIAL_AUCTION
            ):
                print(
                    f"Bid for {game.state.phase_state.company.name}: {game.state.phase_state.current_bid} ({game.state.phase_state.current_bidder})"
                )
                bid = tree_input(
                    f"Player {game.state.next_player_id} (£{game.state.player_cash[game.state.next_player_id]}): ",
                    tree,
                    game.state,
                )
                if int(bid) in game.state.permitted_actions:
                    action = int(bid)
            else:
                print_terrain(TERRAIN, game)
                print_holdings(game.state)
                print_cube_display(game.state)
                print_companies(game.state)
                print([(i, j) for i, j in enumerate(Action)])
                print(f"Player is {game.state.next_player_id}")
                print(f"Permitted actions: {game.state.permitted_actions}")
                if game.state.stage == InTurnStage.REMOVE_ADD_CUBES:
                    remove = None
                    add = None
                    while remove == None or add == None:
                        try:
                            cube_to_remove = tree_input(
                                "Cube to remove, add: ", tree, game.state
                            )
                            remove, add = (
                                int(cube) for cube in cube_to_remove.split(",")
                            )
                        except:
                            pass
                        action = (remove, add)
                elif game.state.stage == InTurnStage.BUILDING_TRACK:
                    print_terrain(TERRAIN, game)
                    x = None
                    y = None
                    while x == None or y == None:
                        try:
                            build_loc = tree_input(
                                "X,Y to build track", tree, game.state
                            )
                            x, y = (int(coord) for coord in build_loc.split(","))
                        except:
                            pass
                    action = (x, y)
                elif game.state.stage == InTurnStage.CHOOSE_PRIVATE_HQ:
                    print_terrain(TERRAIN, game)
                    x = None
                    y = None
                    while x == None or y == None:
                        try:
                            build_loc = tree_input("X,Y of HQ", tree, game.state)
                            x, y = (int(coord) for coord in build_loc.split(","))
                        except:
                            pass
                    action = (x, y)
                elif game.state.stage == InTurnStage.TAKE_RESOURCES:
                    print_terrain(TERRAIN, game)
                    x = None
                    y = None
                    while x == None or y == None:
                        try:
                            take_loc = tree_input(
                                "X,Y to take resource from", tree, game.state
                            )
                            x, y = (int(coord) for coord in take_loc.split(","))
                        except:
                            pass
                    action = (x, y)
                elif game.state.stage == InTurnStage.CHOOSE_MERGE_COS:
                    merge_options = game.state.get_current_player_merge_options()
                    print("Merge options")
                    for i, j in enumerate(merge_options):
                        print(f"{i}: {j}")
                    merge_option = tree_input("Choose merge option", tree, game.state)
                    action = int(merge_option)
                elif game.state.stage == InTurnStage.CHOOSE_AUCTION:
                    print_holdings(game.state)
                    auctions_available = [
                        company
                        for company in COMPANY
                        if len(game.state.company_state[company].shareholders)
                        < COMPANIES[company].stock_available
                    ]
                    for i, j in enumerate(auctions_available):
                        print(f"{i}: {j}")
                    auction_option = tree_input(
                        "Choose share to auction", tree, game.state
                    )
                    action = int(auction_option)
                elif game.state.stage == InTurnStage.CHOOSE_BOND_CO:
                    companies_held = [
                        i
                        for i in game.state.get_current_player_companies_held()
                        if not COMPANIES[i].private
                    ]
                    for i, j in enumerate(companies_held):
                        print(f"{i}: {j}")
                    bond_input = tree_input(
                        "Choose company to issue bond", tree, game.state
                    )
                    action = int(bond_input)
                elif game.state.stage == InTurnStage.CHOOSE_BOND_CERT:
                    for i, j in enumerate(game.state.bonds_remaining):
                        print(f"{i}: {j}")
                    bond_input = tree_input("Choose bond to issue", tree, game.state)
                    action = int(bond_input)
                elif game.state.stage == InTurnStage.CHOOSE_TAKE_RESOURCE_CO:
                    companies_held = game.state.get_current_player_companies_held()
                    for i, j in enumerate(companies_held):
                        print(f"{i}: {j}")
                    resource_input = tree_input(
                        "Choose company to take resource from", tree, game.state
                    )
                    action = int(resource_input)
                elif game.state.stage == InTurnStage.CHOOSE_TRACK_CO:
                    companies_held = game.state.get_current_player_companies_held()
                    for i, j in enumerate(companies_held):
                        print(f"{i}: {j}")
                    track_input = tree_input(
                        "Choose company to build track for", tree, game.state
                    )
                    action = int(track_input)
            if action not in game.state.permitted_actions:
                print("Invalid action")
                action = None

        game.act(action)
