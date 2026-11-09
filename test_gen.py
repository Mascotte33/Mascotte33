"""Run: python test_gen.py"""
import random

import gen

assert gen.pacman_is_caught((2, 0), (1, 0), [(1, 0)], [(2, 0)]), "swap must count as a catch"
assert gen.pacman_is_caught((2, 0), (1, 0), [(2, 0)], [(3, 0)]), "same square must count"
assert not gen.pacman_is_caught((2, 0), (1, 0), [(5, 5)], [(5, 4)])
game = gen.play_one_game({(0, 0), (9, 6)}, 10, 7, random.Random(1))
assert game["caught"] or set(game["eaten"]) == {(0, 0), (9, 6)}, "game ends on a catch or empty board"
print("ok")
for seed in range(50):
    game = gen.play_one_game({(0, 0), (9, 6), (5, 0)}, 10, 7, random.Random(seed))
    if game["caught"]:
        assert game["pacman"][-1] in game["ghosts"][-1], "the catching ghost sits on Pac-Man"
print("ok catches")
