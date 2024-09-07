import pytest
import tempfile
import os

import c4.m2game
import mon2y


@pytest.mark.parametrize(
    "game", [(c4.m2game.initialize_game, c4.m2game.act)], ids=["c4"]
)
def test_train(game):
    with tempfile.TemporaryDirectory() as folder:
        mon2y.train(
            game[0],
            game[1],
            iterations=10,
            episodes=1,
            report_location=folder,
        )
