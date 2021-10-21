import math, sys
from lux.game import Game
from lux.game_map import Cell, Position, RESOURCE_TYPES
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate

import logging
import math

logging.basicConfig(filename='../output.log', level=logging.INFO)

DIRECTIONS = Constants.DIRECTIONS
game_state = None

gather_rate = {"wood":20, "coal":5, "uranium":2}
fuel_conversion = {"wood":1, "coal":10, "uranium":40}
gather_iteration = {"uranium":1, "coal":2, "wood":3}

# Functions for common actions -- JA

def pos_to_tuple(position):
    return (position.x,position.y)

def get_resource_tiles(width, height):
        global game_state
        
        resource_tiles: list[Cell] = []
        resource_positions: set(Cell) = set()
        for y in range(height):
            for x in range(width):
                cell = game_state.map.get_cell(x, y)
                if cell.has_resource():
                    resource_tiles.append(cell)
                    resource_positions.add((cell.pos.x, cell.pos.y))
        return resource_tiles, resource_positions

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
        if resource_tile.pos.x == 0:
            x = 10
    return None

def get_rich_cells(resource_tiles):
    global game_state
    game_map = game_state.map

    cell_data = {}
    for resource_tile in resource_tiles:
        if resource_tile.has_resource():
            resource_position = pos_to_tuple(resource_tile.pos)
            resource_data = {"position":resource_position, "resource":resource_tile.resource}
            shifts = [(1,0), (-1,0), (0,1), (0,-1), (0,0)]
            for shift in shifts:
                cell = (resource_position[0] + shift[0], resource_position[1] + shift[1])
                if cell[0] >= game_map.width or cell [1] >= game_map.height or cell[0] < 0 or cell[1] < 0:
                    continue
                if cell in cell_data:
                        cell_data[cell]["resource_tiles"].append(resource_data)
                        cell_data[cell]["types"].add(resource_data["resource"].type)
                else:
                    cell_data[cell] = {"resource_tiles":[]}
                    cell_data[cell]["resource_tiles"].append(resource_data)
                    cell_data[cell]["types"] = set()
                    cell_data[cell]["types"].add(resource_data["resource"].type)
    for cell in cell_data:
        cell_data[cell]["resources"] = len(cell_data[cell]["resource_tiles"])

        for r_tile in cell_data[cell]["resource_tiles"]:
            resource = r_tile["resource"]
            resource_type = r_tile["resource"].type
            if resource_type in cell_data[cell]:
                cell_data[cell][resource_type]["tiles"] += 1
                cell_data[cell][resource_type]["tot_amount"] += resource.amount
                if cell_data[cell][resource_type]["min_amount"] > resource.amount:
                    cell_data[cell][resource_type]["min_amount"] = resource.amount
            else:
                cell_data[cell][resource_type] = {"tiles":1, "min_amount":resource.amount, "tot_amount":resource.amount}
                # cell_data[cell]["wood"] = {"tiles":0, "min_amount":0, "tot_amount":0}
                # cell_data[cell]["coal"] = {"tiles":0, "min_amount":0, "tot_amount":0}
                # cell_data[cell]["uranium"] = {"tiles":0, "min_amount":0, "tot_amount":0}
                # cell_data[cell][resource_type]["tiles"] = 1
                # cell_data[cell][resource_type]["min_amount"] = resource.amount
                # cell_data[cell][resource_type]["tot_amount"] = resource.amount
                # avoids dict.get()

            cell_data[cell]["road"] = game_map.get_cell(*cell).road
            cell_data[cell]["citytile"] = game_map.get_cell(*cell).citytile

    #logging.info(cell_data)
    return cell_data

def calculate_gathering(unit, cell, resources, amount_to_gather):
    global fuel_conversion
    global gather_rate

    unit_space = unit.get_cargo_space_left()
    space_used = 0
    gathered = 0
    turns = 0
    loop = True
    while loop:
        turns += 1
        sorted_resources = sorted(resources, key = lambda x: gather_iteration[x])
        for resource in sorted_resources:
            if resource not in cell:
                continue
            if gathered < amount_to_gather:
                if space_used <= unit_space:
                    space_used += gather_rate[resource]
                    gathered += cell.get(resource,{"tiles":0})["tiles"] * gather_rate[resource] * fuel_conversion[resource]
                else:
                    loop = False
                    break ## Not enough space.
            else:
                loop = False
                break ## Gathered enough.
    return {"turns":turns, "gathered":gathered}


def get_best_cell(player, unit, cell_data, resources, dest = None, value = "resource", amount = "fill", strict = False):
    if dest is None:
        dest = unit.pos
    potential_cells = cell_data.copy()
    for cell in cell_data:
        if not any(resource in cell_data[cell]["types"] for resource in resources):
            del potential_cells[cell]
        if strict and not set(resources) == cell_data[cell]["types"]:
            del potential_cells[cell]

    potential_cells = dict(sorted(potential_cells.items(), key=lambda x: tuple([x[1].get(resource,{"tiles":0})["tiles"] for resource in resources]), reverse = True))
    #logging.info(potential_cells)
    global fuel_conversion
    global gather_rate

    unit_space = unit.get_cargo_space_left()

    if value == "resource":
        if amount == "fill":
            amount_to_gather = unit_space
        else:
            amount_to_gather = min(amount, unit_space)
    if value == "fuel":
        if amount == "fill":
            amount_to_gather = unit_space * 40
        else:
            amount_to_gather = min(amount, unit_space * 40)  
    value_per_turn = dict()
    for cell in potential_cells:
        if value == "fuel":
            gather_info = calculate_gathering(unit, potential_cells[cell], resources, amount_to_gather)
            if gather_info["gathered"] >= amount_to_gather or amount == "fill":
                gather_per_turn = gather_info["gathered"]/gather_info["turns"]
            else:
                continue
        elif value == "resource":
            gather_per_turn = sum(potential_cells[cell].get(resource,{"tiles":0})["tiles"] * gather_rate[resource] for resource in resources)
        ## Replace the distance calculation with road-aware version for a given route.
        distance_to = unit.pos.distance_to(Position(*cell))
        distance_from = Position(*cell).distance_to(dest)
        turns_of_gathering = math.ceil(amount_to_gather/gather_per_turn)
        value_per_turn[cell] = amount_to_gather/((distance_to+distance_from+turns_of_gathering)*2)
    value_per_turn = sorted(value_per_turn.items(), key = lambda x: x[1], reverse = True)
    logging.info(dict(value_per_turn))
    return value_per_turn[0][0], value_per_turn[1][0]


# def get_simple_path(pos):
#     for 


def get_resource_tile_map(resource_positions):
    clustered = dict()
    clusters = {}
    counter = 0
    # for resource_position in resource_positions:
    logging.info(resource_positions)

    shifts = [(1,0),(2,0),(-1,0),(-2,0),(0,1),(0,2),(0,-1),(0,-2),(1,1),(1,-1),(-1,1),(-1,-1)]

    for resource_position in resource_positions:
        if resource_position in clustered:
            parent_in_cluster = True
            cluster_id = clustered[resource_position]
        else:
            parent_in_cluster = False

        for shift in shifts:
            nearby = (resource_position[0] + shift[0], resource_position[1] + shift[1])
            if nearby in resource_positions:
                if parent_in_cluster:
                    if nearby in clustered:
                        if cluster_id == clustered[nearby]:
                            continue
                        for tile in clusters[clustered[nearby]]:
                            clustered[tile] = cluster_id
                        clusters[cluster_id].union(clusters[clustered[nearby]])
                        del clusters[clustered[nearby]]
                    else:
                        clustered[nearby] = cluster_id
                        clusters[cluster_id].add(nearby)
                else:
                    cluster_id = counter
                    clustered[nearby] = cluster_id
                    clustered[resource_position] = cluster_id
                    clusters[cluster_id] = set()
                    clusters[cluster_id].add(resource_position)
                    clusters[cluster_id].add(nearby)
                    parent_in_cluster = True
                    counter += 1
    #logging.info(clusters)
    return clusters

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
    
    #cluster_map = get_resource_tile_map(resource_positions)


    # we iterate over all our units and do something with them
    for unit in player.units:

        if unit.get_cargo_space_left() > 0:
            resource_tiles, resource_positions = get_resource_tiles(width, height)
            cell_data = get_rich_cells(resource_tiles)
            best_cell, best_cell_2 = get_best_cell(player, player.units[0], cell_data, ["wood", "coal", "uranium"], value = "fuel", amount = 3999)
            actions.append(annotate.circle(*best_cell))
            actions.append(annotate.circle(*best_cell_2))
            actions.append(annotate.x(player.units[0].pos.x,player.units[0].pos.y))

        if unit.is_worker() and unit.can_act():
            if unit.get_cargo_space_left() > 0:


                # resource_tiles, resource_positions = get_resource_tiles(width, height)
                # cell_data = get_rich_cells(resource_tiles)
                # best_cell = get_best_cell(player, player.units[0], cell_data, ["wood", "coal", "uranium"], value = "fuel", amount = "fill")
                # actions.append(annotate.circle(*best_cell))

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

    # for position in cell_data:
    #     if cell_data[position]["resources"] > 1:
    #         actions.append(annotate.circle(position[0], position[1]))
    #     else:
    #         actions.append(annotate.x(position[0], position[1]))
    
    

    return actions


## Just iterate through all positions and see where you hit multiple resources. Put an x there.

# {position:(8,10),mineable:3,resources:{wood:2, uranium:1}}