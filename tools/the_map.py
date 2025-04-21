
import uuid
from typing import List, Dict
from pydantic import BaseModel
from sqlmodel import SQLModel, Field
from datetime import datetime

# flat-top hex grid
# top surface is exit zero, number increases clockwise so the 6 sides are 0..5 ↑↗↘↓↙↖
# 0 1 2 3 4 5

class HexGrid:
    def __init__(self, size: int):
        self.size = size

    def get_coordinates(self, room_id: int) -> Tuple[int, int]:
        # calculate coordinates based on the hex grid
        x = room_id % self.size
        y = room_id // self.size
        return (x, y)

    def get_neighbor(self, room_id: int, direction: int) -> int:
        ini_x, ini_y = self.get_coordinates(room_id)
        final_x, final_y = ini_x, ini_y
        # calculate neighbor ids based on the hex grid, then see if they exist in the map
        if direction == 0:
            final_x = ini_x + 1
            final_y = ini_y
        elif direction == 1:
            final_x = ini_x + 1
            final_y = ini_y - 1
        elif direction == 2:
            final_x = ini_x
            final_y = ini_y - 1
        elif direction == 3:
            final_x = ini_x - 1
            final_y = ini_y - 1
        elif direction == 4:
            final_x = ini_x - 1
            final_y = ini_y
        elif direction == 5:
            final_x = ini_x - 1
            final_y = ini_y + 1
        else:
            raise ValueError(f"Invalid direction {direction}")
        if final_x < 0 or final_x >= self.size or final_y < 0 or final_y >= self.size:
            return None
        return final_x + final_y * self.size

class Room(BaseModel):
    id: int
    name: str
    description: str
    owner: str # agent id of the owner, zero if publicly owned
    exits: List[bool]
    agents: List[str] = Field(default="[]") # list of agent ids
    items: List[str] = Field(default="[]") # list of item ids
    apps: List[str] = Field(default="[]") # list of app ids
    doors: List[bool] = Field(default=[False]*6) # list of door states
    total_interactions: int = Field(default=0) # total number of interactions in the room

class MapStateDBO(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    owner: str # agent id of the owner, zero if publicly owned
    name: str
    description: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    rooms: Dict[int, Room] = Field(default={}) # room id => room, hex grid
    agents: Dict[str, int] = Field(default={}) # agent id => room id, agents current room
    occupied_rooms: Dict[int, bool] = Field(default={}) # room id => bool, true if occupied


class MapManager:
    def __init__(self, owner_id: str = "0"):
        self.maps = {}
        self.owner_id = owner_id # agent id of the owner, zero if publicly owned
        # TODO: create a default map

    def get_map(self, map_id: str) -> MapStateDBO:
        return self.maps[map_id]

    def search_rooms(self, map_id: str, query: str) -> List[int]:
        # search for rooms by name or description
        # TODO: make this better and fuzzy
        return [room_id for room_id, room in self.maps[map_id].rooms.items() if query in room.name or query in room.description]

    def chat_in_room(self, map_id: str, room_id: int, sender_id: str, message: str) -> MapStateDBO:
        # add message to room
        self.maps[map_id].rooms[room_id].messages.append(message)
        return self.maps[map_id]

    def get_map_details(self, map_id: str, sender_id: str) -> MapStateDBO:
        # return well formatted string of the map
        is_in_map = sender_id in self.maps[map_id].agents

        # error is map does not exist
        if map_id not in self.maps:
            raise f"Map {map_id} does not exist"

        output_string = f"Map ({map_id}) {self.maps[map_id].name} details:\n"

        # stats and popular room


        if is_in_map:
            room_id = self.maps[map_id].agents[sender_id]
            room = self.maps[map_id].rooms[room_id]
            output_string += f"You are in this map at room {room_id}\n"
            # detail
        else:
            output_string += f"You are not in map {map_id}\n"

        return output_string

    def create_map(self, name:str, description:str, size:int) -> MapStateDBO:
        map = MapStateDBO(id=str(uuid.uuid4()), name=name, description=description, owner=self.owner_id)
        self.maps[map.id] = map
        self.hex_grid = HexGrid(size)
        # TODO: create a default room with mapmanager app
        self.add_room(map.id, 0, "Map Manager", "Map Manager")
        return map

    def add_room(self, map_id: str, room_id: int, name:str, description:str) -> MapStateDBO:
        # check if room_id is already in the map
        if room_id in self.maps[map_id].rooms:
            raise ValueError(f"Room {room_id} already exists in map {map_id}")
        room = Room(id=room_id, name=name, description=description, exits=[False]*6)
        self.maps[map_id].rooms[room_id] = room
        return self.maps[map_id]
    
    def delete_room(self, map_id: str, room_id: int) -> MapStateDBO:
        # must be the owner of the map
        if self.maps[map_id].owner != self.owner_id:
            raise ValueError(f"You are not the owner of map {map_id}")
        # remove all agents from the room
        for agent_id in self.maps[map_id].agents:
            if self.maps[map_id].agents[agent_id] == room_id:
                del self.maps[map_id].agents[agent_id]
            
        del self.maps[map_id].rooms[room_id]
        return self.maps[map_id]
    
    def enter_room(self, map_id: str, agent_id: str, room_id: int, door_direction: int, sender_id: str) -> MapStateDBO:
        # todo: add ban list for entering rooms
        # sender must be the agent
        if sender_id != agent_id:
            raise ValueError(f"You are not the agent {agent_id}")
        # can only enter through an open door
        if not self.maps[map_id].rooms[room_id].doors[door_direction]:
            raise ValueError(f"Room {room_id} has no door in direction {door_direction}")
        self.maps[map_id].agents[agent_id] = room_id
        self.maps[map_id].occupied_rooms[room_id] = True
        self.maps[map_id].rooms[room_id].agents.append(agent_id)
            
    def exit_room(self, map_id: str, agent_id: str, room_id: int, sender_id: str) -> MapStateDBO:
        # sender must be the agent or owner of map or room
        if sender_id != agent_id and sender_id != self.owner_id and sender_id != self.maps[map_id].rooms[room_id].owner:
            raise ValueError(f"You are not the agent {agent_id} or the owner of map {map_id} or the owner of room {room_id}")
        self.maps[map_id].agents[agent_id] = room_id
        self.maps[map_id].occupied_rooms[room_id] = False
        self.maps[map_id].rooms[room_id].agents.remove(agent_id)      
    
    def add_item(self, map_id: str, item_id: str, room_id: int, sender_id: str) -> MapStateDBO:
        # must be owner of room or room must be publicly owned
        if sender_id != self.owner_id and sender_id != self.maps[map_id].rooms[room_id].owner:
            raise ValueError(f"You are not the owner of room {room_id}")
        self.maps[map_id].rooms[room_id].items.append(item_id)
        return self.maps[map_id]
      
    def add_app(self, map_id: str, app_id: str, room_id: int, sender_id: str) -> MapStateDBO:
        # must be owner of room or room must be publicly owned
        if sender_id != self.owner_id and sender_id != self.maps[map_id].rooms[room_id].owner:
            raise ValueError(f"You are not the owner of room {room_id}")
        self.maps[map_id].rooms[room_id].apps.append(app_id)
        return self.maps[map_id]
    
    def remove_item(self, map_id: str, item_id: str, room_id: int, sender_id: str) -> MapStateDBO:
        # must be owner of room or room must be publicly owned
        if sender_id != self.owner_id and sender_id != self.maps[map_id].rooms[room_id].owner:
            raise ValueError(f"You are not the owner of room {room_id}")
        del self.maps[map_id].items[item_id]
        return self.maps[map_id]
    
    def remove_app(self, map_id: str, app_id: str, room_id: int, sender_id: str) -> MapStateDBO:
        # must be owner of room or room must be publicly owned
        if sender_id != self.owner_id and sender_id != self.maps[map_id].rooms[room_id].owner:
            raise ValueError(f"You are not the owner of room {room_id}")
        del self.maps[map_id].apps[app_id]
        return self.maps[map_id]
    
    def get_room_by_id(self, map_id: str, room_id: int, sender_id: str) -> Room:
        return self.maps[map_id].rooms[room_id]
    
    def get_neighbors(self, map_id: str, room_id: int, sender_id: str) -> List[int]:
        # calculate neighbor ids based on the hex grid, then see if they exist in the map
        neighbors = [
            self.hex_grid.get_neighbor(room_id, 0),
            self.hex_grid.get_neighbor(room_id, 1),
            self.hex_grid.get_neighbor(room_id, 2),
            self.hex_grid.get_neighbor(room_id, 3),
            self.hex_grid.get_neighbor(room_id, 4),
            self.hex_grid.get_neighbor(room_id, 5),
        ]

        # filter out None values
        neighbors = [neighbor for neighbor in neighbors if neighbor is not None]
        
        return neighbors
    
    def claim_room(self, map_id: str, room_id: int, agent_id: str, sender_id: str) -> MapStateDBO:
        # room must not exist in the map
        if room_id in self.maps[map_id].rooms:
            raise ValueError(f"Room {room_id} already exists in map {map_id}")
        self.maps[map_id].agents[agent_id] = room_id
        return self.maps[map_id]
    
    def release_room(self, map_id: str, agent_id: str, room_id: int, sender_id: str) -> MapStateDBO:
        # agent must be the owner of the room or the owner of the map
        if sender_id != self.maps[map_id].rooms[room_id].owner and sender_id != self.owner_id:
            raise ValueError(f"You are not the owner of room {room_id}")
        # sets room to publicly owned
        self.maps[map_id].rooms[room_id].owner = "0"
        return self.maps[map_id]
    
    def remove_room(self, map_id: str, room_id: int, sender_id: str) -> MapStateDBO:
        # must be owner of map or room
        if sender_id != self.owner_id and sender_id != self.maps[map_id].rooms[room_id].owner:
            raise ValueError(f"You are not the owner of room {room_id}")
        del self.maps[map_id].rooms[room_id]
        return self.maps[map_id]
    
    def close_door(self, map_id: str, room_id: int, direction: int, sender_id: str) -> MapStateDBO:
        # must be owner of room or room must be publicly owned
        if sender_id != self.owner_id and sender_id != self.maps[map_id].rooms[room_id].owner:
            raise ValueError(f"You are not the owner of room {room_id}")
        self.maps[map_id].rooms[room_id].exits[direction] = False
        return self.maps[map_id]
    
    def open_door(self, map_id: str, room_id: int, direction: int, sender_id: str) -> MapStateDBO:
        # must be owner of room or room must be publicly owned
        if sender_id != self.owner_id and sender_id != self.maps[map_id].rooms[room_id].owner:
            raise ValueError(f"You are not the owner of room {room_id}")
        self.maps[map_id].rooms[room_id].exits[direction] = True
        return self.maps[map_id]
    
    