import math, sys
from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate
import logging

logging.basicConfig(filename='../output.log', level=logging.INFO)

DIRECTIONS = Constants.DIRECTIONS
game_state = None

# Functions for common actions -- JA
def get_resource_tiles(width, height):
        global game_state
        
        resource_tiles: list[Cell] = []
        for y in range(height):
            for x in range(width):
                cell = game_state.map.get_cell(x, y)
                if cell.has_resource():
                    resource_tiles.append(cell)
        return resource_tiles

def get_closest_resource_tile(player, unit, resource_tiles):
    closest_dist = math.inf
    closest_resource_tile = None
    for resource_tile in resource_tiles:
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.COAL and not player.researched_coal(): continue
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.URANIUM and not player.researched_uranium(): continue
        dist = resource_tile.pos.distance_to(unit.pos)
        if dist < closest_dist:
            closest_dist = dist
            closest_resource_tile = resource_tile
    return closest_resource_tile

def get_closest_city_tile(player, unit):
    if len(player.cities) > 0:
        closest_dist = math.inf
        closest_city_tile = None
        for k, city in player.cities.items():
            for city_tile in city.citytiles:
                dist = city_tile.pos.distance_to(unit.pos)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_city_tile = city_tile
        return closest_city_tile
    else:
        return None

def get_optimal_city_tile(player, city, resource_tiles):
    for resource_tile in resource_tiles:
        if resource_tile.pos.x ==0:
            x = 10
    return None

def get_resource_tile_map(resource_tiles):
    clustered = {}
    for resource_tile in resource_tiles:
        if resource_tile.pos in clustered:
            continue

def agent(observation, configuration):
    global game_state

    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player
    else:
        game_state._update(observation["updates"])
    
    actions = []

    ### AI Code goes down here! ###

    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    width, height = game_state.map.width, game_state.map.height


    #
    logging.info("Hello")

    resource_tiles = get_resource_tiles(width, height)
    # we iterate over all our units and do something with them
    for unit in player.units:
        if unit.is_worker() and unit.can_act():
            if unit.get_cargo_space_left() > 0:
                # if the unit is a worker and we have space in cargo, lets find the nearest resource tile and try to mine it
                closest_resource_tile = get_closest_resource_tile(player, unit, resource_tiles)
                if closest_resource_tile is not None:
                    actions.append(unit.move(unit.pos.direction_to(closest_resource_tile.pos)))
            else:
                # if unit is a worker and there is no cargo space left, and we have cities, lets return to them
                    closest_city_tile = get_closest_city_tile(player, unit)
                    if closest_city_tile is not None:
                        move_dir = unit.pos.direction_to(closest_city_tile.pos)
                        actions.append(unit.move(move_dir))

    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(0, 0))
    
    return actions
