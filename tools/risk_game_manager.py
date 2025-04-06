import random
import uuid
from enum import Enum
from typing import Dict, List, Tuple, Optional, Set


class GameStatus(Enum):
    WAITING_FOR_PLAYERS = 0
    IN_PROGRESS = 1
    COMPLETED = 2


class TerritoryManager:
    def __init__(self, territory_names: List[str], connections: Dict[str, List[str]]):
        self.territories = territory_names
        self.connections = connections

    def get_connected_territories(self, territory: str) -> List[str]:
        return self.connections.get(territory, [])
    
    def are_connected(self, territory1: str, territory2: str) -> bool:
        return territory2 in self.connections.get(territory1, [])


class Player:
    def __init__(self, player_id: str, name: str):
        self.id = player_id
        self.name = name
        self.territories = set()
        self.available_troops = 0


class Game:
    def __init__(self, game_id: str, max_players: int, territory_manager: TerritoryManager):
        self.id = game_id
        self.status = GameStatus.WAITING_FOR_PLAYERS
        self.players = {}
        self.max_players = max_players
        self.current_player_id = None
        self.territory_manager = territory_manager
        self.territory_ownership = {}  # territory: player_id
        self.territory_troops = {}  # territory: troop_count
        self.turn_phase = None  # "deploy", "attack", "fortify"
        self.turn_number = 0
        self.winner = None
        self.player_order = []


class SimpleRiskGame:
    def __init__(self):
        self.games = {}
        self.default_territory_manager = self._create_default_territory_manager()
    
    def _create_default_territory_manager(self) -> TerritoryManager:
        # A simplified map with continents and territories
        territories = [
            "North America 1", "North America 2", "North America 3",
            "South America 1", "South America 2",
            "Europe 1", "Europe 2", "Europe 3",
            "Africa 1", "Africa 2", "Africa 3",
            "Asia 1", "Asia 2", "Asia 3", "Asia 4",
            "Australia 1", "Australia 2"
        ]
        
        # Define connections between territories
        connections = {
            "North America 1": ["North America 2", "Europe 1"],
            "North America 2": ["North America 1", "North America 3", "South America 1"],
            "North America 3": ["North America 2", "Asia 1"],
            "South America 1": ["North America 2", "South America 2", "Africa 1"],
            "South America 2": ["South America 1"],
            "Europe 1": ["North America 1", "Europe 2", "Africa 1"],
            "Europe 2": ["Europe 1", "Europe 3", "Asia 1"],
            "Europe 3": ["Europe 2", "Asia 2", "Africa 2"],
            "Africa 1": ["South America 1", "Europe 1", "Africa 2"],
            "Africa 2": ["Africa 1", "Africa 3", "Europe 3"],
            "Africa 3": ["Africa 2", "Australia 1"],
            "Asia 1": ["North America 3", "Europe 2", "Asia 2"],
            "Asia 2": ["Asia 1", "Europe 3", "Asia 3"],
            "Asia 3": ["Asia 2", "Asia 4", "Australia 2"],
            "Asia 4": ["Asia 3", "Australia 2"],
            "Australia 1": ["Africa 3", "Australia 2"],
            "Australia 2": ["Australia 1", "Asia 3", "Asia 4"]
        }
        
        # Make connections bidirectional if not already
        for territory, connected in list(connections.items()):
            for conn in connected:
                if territory not in connections.get(conn, []):
                    connections.setdefault(conn, []).append(territory)
        
        return TerritoryManager(territories, connections)

    def get_rules(self) -> Dict:
        """Returns the rules of the game."""
        return {
            "name": "Simple Risk",
            "description": "A simplified version of Risk, a game of world domination",
            "phases": [
                "deploy - Place your reinforcement troops on your territories",
                "attack - Attack neighboring territories",
                "fortify - Move troops between your connected territories"
            ],
            "victory_condition": "Control all territories on the map",
            "player_count": "2-6 players",
            "continents": {
                "North America": ["North America 1", "North America 2", "North America 3"],
                "South America": ["South America 1", "South America 2"],
                "Europe": ["Europe 1", "Europe 2", "Europe 3"],
                "Africa": ["Africa 1", "Africa 2", "Africa 3"],
                "Asia": ["Asia 1", "Asia 2", "Asia 3", "Asia 4"],
                "Australia": ["Australia 1", "Australia 2"]
            },
            "continent_bonuses": {
                "North America": 5,
                "South America": 2,
                "Europe": 5,
                "Africa": 3,
                "Asia": 7,
                "Australia": 2
            },
            "commands": {
                "deploy": "deploy <territory> <troops>",
                "attack": "attack <from_territory> <to_territory> <troops>",
                "fortify": "fortify <from_territory> <to_territory> <troops>",
                "end_phase": "end_phase"
            }
        }

    def create_game(self, player_id: str, player_name: str, max_players: int = 6) -> Dict:
        """Creates a new game and adds the creator as the first player."""
        if max_players < 2 or max_players > 6:
            return {"error": "Player count must be between 2 and 6"}
        
        game_id = str(uuid.uuid4())
        game = Game(game_id, max_players, self.default_territory_manager)
        self.games[game_id] = game
        
        # Add the creator as the first player
        return self._add_player_to_game(game, player_id, player_name)

    def _add_player_to_game(self, game: Game, player_id: str, player_name: str) -> Dict:
        """Helper method to add a player to a game."""
        if player_id in game.players:
            return {"error": "Player already in game", "game_id": game.id}
            
        if len(game.players) >= game.max_players:
            return {"error": "Game is full", "game_id": game.id}
            
        if game.status != GameStatus.WAITING_FOR_PLAYERS:
            return {"error": "Cannot join game in progress", "game_id": game.id}
            
        player = Player(player_id, player_name)
        game.players[player_id] = player
        game.player_order.append(player_id)
        
        return {
            "success": True,
            "game_id": game.id,
            "player_id": player_id,
            "players_joined": len(game.players),
            "players_needed": game.max_players - len(game.players),
            "status": game.status.name
        }

    def join_game(self, game_id: str, player_id: str, player_name: str) -> Dict:
        """Allows a player to join an existing game."""
        if game_id not in self.games:
            return {"error": "Game not found"}
            
        game = self.games[game_id]
        result = self._add_player_to_game(game, player_id, player_name)
        
        # If all players have joined, start the game
        if "success" in result and len(game.players) == game.max_players:
            self._start_game(game)
            result["status"] = game.status.name
            result["started"] = True
            
        return result

    def _start_game(self, game: Game) -> None:
        """Initialize the game once all players have joined."""
        game.status = GameStatus.IN_PROGRESS
        game.turn_number = 1
        
        # Randomly determine player order
        random.shuffle(game.player_order)
        game.current_player_id = game.player_order[0]
        
        # Distribute territories randomly
        territories = game.territory_manager.territories.copy()
        random.shuffle(territories)
        
        players_cycle = game.player_order.copy()
        for territory in territories:
            if not players_cycle:
                players_cycle = game.player_order.copy()
            
            player_id = players_cycle.pop(0)
            game.territory_ownership[territory] = player_id
            game.territory_troops[territory] = 1
            game.players[player_id].territories.add(territory)
        
        # Give initial troops to place
        self._calculate_reinforcements(game)
        game.turn_phase = "deploy"

    def _calculate_reinforcements(self, game: Game) -> None:
        """Calculate reinforcements for the current player."""
        player = game.players[game.current_player_id]
        
        # Base reinforcements: max(3, territories / 3)
        territory_count = len(player.territories)
        reinforcements = max(3, territory_count // 3)
        
        # Add continent bonuses
        continents = self.get_rules()["continents"]
        continent_bonuses = self.get_rules()["continent_bonuses"]
        
        for continent, territories in continents.items():
            if all(t in player.territories for t in territories):
                reinforcements += continent_bonuses[continent]
        
        player.available_troops = reinforcements

    def get_game_state(self, game_id: str, player_id: str) -> Dict:
        """Returns the current state of the game."""
        if game_id not in self.games:
            return {"error": "Game not found"}
            
        game = self.games[game_id]
        
        if player_id not in game.players:
            return {"error": "Player not in game"}
            
        # Basic game info
        state = {
            "game_id": game.id,
            "status": game.status.name,
            "turn_number": game.turn_number,
            "players": {p_id: p.name for p_id, p in game.players.items()},
            "current_player": game.current_player_id,
            "current_phase": game.turn_phase,
        }
        
        # Add winner if game is completed
        if game.status == GameStatus.COMPLETED and game.winner:
            state["winner"] = game.winner
            state["winner_name"] = game.players[game.winner].name
        
        # Add territories info
        state["territories"] = {
            territory: {
                "owner": game.territory_ownership.get(territory),
                "troops": game.territory_troops.get(territory, 0)
            }
            for territory in game.territory_manager.territories
        }
        
        # Add player-specific info
        player = game.players[player_id]
        state["your_turn"] = (player_id == game.current_player_id)
        state["your_territories"] = list(player.territories)
        state["available_troops"] = player.available_troops
        
        # Add valid actions based on current phase
        if player_id == game.current_player_id:
            if game.turn_phase == "deploy":
                state["valid_actions"] = self._get_valid_deploy_actions(game, player_id)
            elif game.turn_phase == "attack":
                state["valid_actions"] = self._get_valid_attack_actions(game, player_id)
            elif game.turn_phase == "fortify":
                state["valid_actions"] = self._get_valid_fortify_actions(game, player_id)
        
        return state

    def _get_valid_deploy_actions(self, game: Game, player_id: str) -> Dict:
        """Returns valid deployment actions for the player."""
        player = game.players[player_id]
        deploy_actions = {
            "territories": list(player.territories),
            "troops_available": player.available_troops
        }
        return deploy_actions

    def _get_valid_attack_actions(self, game: Game, player_id: str) -> Dict:
        """Returns valid attack actions for the player."""
        attack_actions = {"possible_attacks": []}
        
        for territory in game.players[player_id].territories:
            troops = game.territory_troops[territory]
            if troops > 1:  # Need at least 2 troops to attack
                connected = game.territory_manager.get_connected_territories(territory)
                for target in connected:
                    if game.territory_ownership.get(target) != player_id:
                        attack_actions["possible_attacks"].append({
                            "from": territory,
                            "to": target,
                            "max_troops": troops - 1
                        })
        
        return attack_actions

    def _get_valid_fortify_actions(self, game: Game, player_id: str) -> Dict:
        """Returns valid fortify actions for the player."""
        fortify_actions = {"possible_moves": []}
        
        for territory in game.players[player_id].territories:
            troops = game.territory_troops[territory]
            if troops > 1:  # Need at least 2 troops to fortify
                # Find connected territories that belong to the player
                connected = [
                    t for t in game.territory_manager.get_connected_territories(territory)
                    if game.territory_ownership.get(t) == player_id
                ]
                
                for target in connected:
                    fortify_actions["possible_moves"].append({
                        "from": territory,
                        "to": target,
                        "max_troops": troops - 1
                    })
        
        return fortify_actions

    def make_move(self, game_id: str, player_id: str, action: str, **params) -> Dict:
        """Execute a move in the game."""
        if game_id not in self.games:
            return {"error": "Game not found"}
            
        game = self.games[game_id]
        
        if game.status != GameStatus.IN_PROGRESS:
            return {"error": "Game is not in progress"}
            
        if player_id != game.current_player_id:
            return {"error": "Not your turn"}
        
        # Handle different actions based on the current phase
        if action == "deploy" and game.turn_phase == "deploy":
            return self._handle_deploy(game, player_id, **params)
        elif action == "attack" and game.turn_phase == "attack":
            return self._handle_attack(game, player_id, **params)
        elif action == "fortify" and game.turn_phase == "fortify":
            return self._handle_fortify(game, player_id, **params)
        elif action == "end_phase":
            return self._handle_end_phase(game, player_id)
        else:
            return {"error": "Invalid action for current phase"}

    def _handle_deploy(self, game: Game, player_id: str, territory: str, troops: int) -> Dict:
        """Handle troop deployment."""
        player = game.players[player_id]
        
        # Validate deployment
        if territory not in player.territories:
            return {"error": "You don't control this territory"}
            
        if troops <= 0 or troops > player.available_troops:
            return {"error": f"Invalid troop count. You have {player.available_troops} available"}
        
        # Execute deployment
        game.territory_troops[territory] = game.territory_troops.get(territory, 0) + troops
        player.available_troops -= troops
        
        result = {
            "success": True,
            "action": "deploy",
            "territory": territory,
            "troops_deployed": troops,
            "troops_remaining": player.available_troops
        }
        
        # If no more troops to deploy, automatically end phase
        if player.available_troops == 0:
            phase_result = self._handle_end_phase(game, player_id)
            result.update(phase_result)
        
        return result

    def _handle_attack(self, game: Game, player_id: str, from_territory: str, to_territory: str, troops: int) -> Dict:
        """Handle attack action."""
        # Validate attack
        if from_territory not in game.players[player_id].territories:
            return {"error": "You don't control the attacking territory"}
            
        if game.territory_ownership.get(to_territory) == player_id:
            return {"error": "You already control the target territory"}
            
        if not game.territory_manager.are_connected(from_territory, to_territory):
            return {"error": "Territories are not connected"}
            
        available_troops = game.territory_troops.get(from_territory, 0) - 1
        if troops <= 0 or troops > available_troops:
            return {"error": f"Invalid troop count. You can attack with up to {available_troops} troops"}
        
        # Simulate battle
        attacking_power = sum(random.randint(1, 6) for _ in range(min(3, troops)))
        defending_troops = game.territory_troops.get(to_territory, 0)
        defending_power = sum(random.randint(1, 6) for _ in range(min(2, defending_troops)))
        
        attack_successful = attacking_power > defending_power
        result = {
            "success": True,
            "action": "attack",
            "from_territory": from_territory,
            "to_territory": to_territory,
            "attacking_troops": troops,
            "defending_troops": defending_troops,
            "attack_successful": attack_successful,
            "battle_details": {
                "attack_roll": attacking_power,
                "defense_roll": defending_power
            }
        }
        
        # Update game state based on battle outcome
        if attack_successful:
            # Transfer territory ownership
            old_owner = game.territory_ownership.get(to_territory)
            game.territory_ownership[to_territory] = player_id
            game.territory_troops[to_territory] = troops
            game.territory_troops[from_territory] -= troops
            
            # Update player territory sets
            game.players[player_id].territories.add(to_territory)
            if old_owner:
                game.players[old_owner].territories.remove(to_territory)
                
                # Check if old owner was eliminated
                if not game.players[old_owner].territories:
                    result["player_eliminated"] = old_owner
            
            # Check for victory
            if len(game.players[player_id].territories) == len(game.territory_manager.territories):
                game.status = GameStatus.COMPLETED
                game.winner = player_id
                result["game_won"] = True
        else:
            # Attacker loses troops
            troops_lost = min(troops, 2)
            game.territory_troops[from_territory] -= troops_lost
            result["troops_lost"] = troops_lost
        
        return result

    def _handle_fortify(self, game: Game, player_id: str, from_territory: str, to_territory: str, troops: int) -> Dict:
        """Handle fortify action."""
        # Validate fortify
        if from_territory not in game.players[player_id].territories:
            return {"error": "You don't control the source territory"}
            
        if to_territory not in game.players[player_id].territories:
            return {"error": "You don't control the destination territory"}
            
        if not game.territory_manager.are_connected(from_territory, to_territory):
            return {"error": "Territories are not connected"}
            
        available_troops = game.territory_troops.get(from_territory, 0) - 1
        if troops <= 0 or troops > available_troops:
            return {"error": f"Invalid troop count. You can move up to {available_troops} troops"}
        
        # Execute fortify
        game.territory_troops[from_territory] -= troops
        game.territory_troops[to_territory] += troops
        
        return {
            "success": True,
            "action": "fortify",
            "from_territory": from_territory,
            "to_territory": to_territory,
            "troops_moved": troops
        }

    def _handle_end_phase(self, game: Game, player_id: str) -> Dict:
        """Handle end phase action."""
        current_phase = game.turn_phase
        result = {
            "success": True,
            "action": "end_phase",
            "phase_ended": current_phase
        }
        
        # Determine next phase
        if current_phase == "deploy":
            game.turn_phase = "attack"
            result["new_phase"] = "attack"
        elif current_phase == "attack":
            game.turn_phase = "fortify"
            result["new_phase"] = "fortify"
        elif current_phase == "fortify":
            # End turn and move to next player
            next_player_idx = (game.player_order.index(player_id) + 1) % len(game.player_order)
            next_player_id = game.player_order[next_player_idx]
            
            game.current_player_id = next_player_id
            game.turn_phase = "deploy"
            
            if next_player_idx == 0:
                game.turn_number += 1
            
            # Calculate reinforcements for next player
            self._calculate_reinforcements(game)
            
            result.update({
                "new_phase": "deploy",
                "next_player": next_player_id,
                "turn_ended": True,
                "new_turn": next_player_idx == 0,
                "turn_number": game.turn_number
            })
        
        return result

    def forfeit(self, game_id: str, player_id: str) -> Dict:
        """Allow a player to forfeit the game."""
        if game_id not in self.games:
            return {"error": "Game not found"}
            
        game = self.games[game_id]
        
        if player_id not in game.players:
            return {"error": "Player not in game"}
            
        if game.status != GameStatus.IN_PROGRESS:
            return {"error": "Game is not in progress"}
        
        # Remove player's territories and reassign to other players randomly
        if player_id in game.players:
            # Get all territories owned by the forfeiting player
            player_territories = list(game.players[player_id].territories)
            
            # Get remaining players
            remaining_players = [p for p in game.player_order if p != player_id and p in game.players]
            
            if not remaining_players:
                # No players left, end the game
                game.status = GameStatus.COMPLETED
                return {
                    "success": True,
                    "game_ended": True,
                    "reason": "All players forfeited"
                }
            
            # Redistribute territories
            for territory in player_territories:
                new_owner = random.choice(remaining_players)
                game.territory_ownership[territory] = new_owner
                game.territory_troops[territory] = max(1, game.territory_troops.get(territory, 0) // 2)
                game.players[new_owner].territories.add(territory)
            
            # Remove player from game
            game.players[player_id].territories.clear()
            game.player_order.remove(player_id)
            
            # If current player forfeited, move to next player
            if game.current_player_id == player_id:
                if game.player_order:
                    game.current_player_id = game.player_order[0]
                    game.turn_phase = "deploy"
                    self._calculate_reinforcements(game)
            
            # Check if only one player remains
            if len(game.player_order) == 1:
                game.status = GameStatus.COMPLETED
                game.winner = game.player_order[0]
                return {
                    "success": True,
                    "game_ended": True,
                    "winner": game.winner,
                    "reason": "All other players forfeited"
                }
            
            return {
                "success": True,
                "player_removed": player_id,
                "territories_redistributed": len(player_territories),
                "players_remaining": len(game.player_order)
            }
        



def main():
    """Test the SimpleRiskGame by simulating a few rounds of gameplay."""
    # Create a game manager
    game_manager = SimpleRiskGame()
    
    # Print game rules
    print("Game Rules:")
    rules = game_manager.get_rules()
    print(f"Game: {rules['name']} - {rules['description']}")
    print(f"Victory Condition: {rules['victory_condition']}")
    print(f"Player Count: {rules['player_count']}")
    print("\n")
    
    # Create test players
    players = [
        {"id": "player1", "name": "Alice"},
        {"id": "player2", "name": "Bob"},
        {"id": "player3", "name": "Charlie"}
    ]
    
    # Create a new game with the first player
    print(f"Creating a new game with {players[0]['name']}...")
    result = game_manager.create_game(players[0]['id'], players[0]['name'], max_players=3)
    game_id = result['game_id']
    print(f"Game created with ID: {game_id}")
    print(f"Status: {result['status']}")
    print(f"Players joined: {result['players_joined']}/{result['players_joined'] + result['players_needed']}")
    print("\n")
    
    # Add remaining players
    for player in players[1:]:
        print(f"Adding {player['name']} to the game...")
        result = game_manager.join_game(game_id, player['id'], player['name'])
        print(f"Status: {result['status']}")
        if 'started' in result and result['started']:
            print("All players joined! Game has started.")
        print("\n")
    
    # Simulate 3 rounds of gameplay
    for round_num in range(1, 4):
        print(f"===== ROUND {round_num} =====")
        
        # Each player takes their turn
        for player in players:
            print(f"\n--- {player['name']}'s Turn ---")
            
            # Get the game state for this player
            state = game_manager.get_game_state(game_id, player['id'])
            
            # Skip if it's not this player's turn
            if not state.get('your_turn', False):
                print(f"Not {player['name']}'s turn. Skipping...")
                continue
            
            print(f"Current phase: {state['current_phase']}")
            
            # DEPLOY PHASE
            if state['current_phase'] == 'deploy':
                print(f"Available troops: {state['available_troops']}")
                
                # Get player territories
                territories = state['your_territories']
                print(f"Owns {len(territories)} territories")
                
                # Deploy troops evenly across territories with preference to borders
                troops_remaining = state['available_troops']
                while troops_remaining > 0 and territories:
                    # Start with first territory in the list
                    target_territory = territories[0]
                    troops_to_deploy = min(troops_remaining, max(1, troops_remaining // len(territories)))
                    
                    print(f"Deploying {troops_to_deploy} troops to {target_territory}")
                    result = game_manager.make_move(
                        game_id, 
                        player['id'], 
                        'deploy', 
                        territory=target_territory, 
                        troops=troops_to_deploy
                    )
                    
                    if 'error' in result:
                        print(f"Error: {result['error']}")
                        break
                    
                    print(f"Deployment successful. {result.get('troops_remaining', 0)} troops remaining.")
                    troops_remaining = result.get('troops_remaining', 0)
                    
                    # If phase ended automatically, print the new phase
                    if 'new_phase' in result:
                        print(f"Phase automatically ended. New phase: {result['new_phase']}")
                    
                    # Rotate territories list for even distribution
                    territories = territories[1:] + [territories[0]]
                
                # If we still have troops to deploy, the phase hasn't ended yet
                if troops_remaining == 0 and 'new_phase' not in result:
                    print("Ending deploy phase manually")
                    result = game_manager.make_move(game_id, player['id'], 'end_phase')
                    print(f"New phase: {result['new_phase']}")
            
            # ATTACK PHASE
            # Get updated state if phase changed
            state = game_manager.get_game_state(game_id, player['id'])
            if state['current_phase'] == 'attack':
                # Check for possible attacks
                attacks = state.get('valid_actions', {}).get('possible_attacks', [])
                if attacks:
                    # Pick the first attack opportunity
                    attack = attacks[0]
                    from_territory = attack['from']
                    to_territory = attack['to']
                    troops = min(attack['max_troops'], 3)  # Use up to 3 troops for attack
                    
                    print(f"Attacking {to_territory} from {from_territory} with {troops} troops")
                    result = game_manager.make_move(
                        game_id,
                        player['id'],
                        'attack',
                        from_territory=from_territory,
                        to_territory=to_territory,
                        troops=troops
                    )
                    
                    if 'error' in result:
                        print(f"Error: {result['error']}")
                    else:
                        print(f"Attack {'successful' if result['attack_successful'] else 'failed'}")
                        print(f"Attack roll: {result['battle_details']['attack_roll']}")
                        print(f"Defense roll: {result['battle_details']['defense_roll']}")
                        
                        if 'game_won' in result and result['game_won']:
                            print(f"{player['name']} has won the game by conquering all territories!")
                            return
                else:
                    print("No valid attacks available")
                
                # End attack phase
                print("Ending attack phase")
                result = game_manager.make_move(game_id, player['id'], 'end_phase')
                print(f"New phase: {result['new_phase']}")
            
            # FORTIFY PHASE
            # Get updated state if phase changed
            state = game_manager.get_game_state(game_id, player['id'])
            if state['current_phase'] == 'fortify':
                # Check for possible fortify moves
                moves = state.get('valid_actions', {}).get('possible_moves', [])
                if moves:
                    # Pick the first fortify opportunity
                    move = moves[0]
                    from_territory = move['from']
                    to_territory = move['to']
                    troops = min(move['max_troops'], 2)  # Move up to 2 troops
                    
                    print(f"Fortifying {to_territory} from {from_territory} with {troops} troops")
                    result = game_manager.make_move(
                        game_id,
                        player['id'],
                        'fortify',
                        from_territory=from_territory,
                        to_territory=to_territory,
                        troops=troops
                    )
                    
                    if 'error' in result:
                        print(f"Error: {result['error']}")
                    else:
                        print(f"Fortification successful. Moved {result['troops_moved']} troops.")
                else:
                    print("No valid fortify moves available")
                
                # End fortify phase and turn
                print("Ending fortify phase")
                result = game_manager.make_move(game_id, player['id'], 'end_phase')
                
                if 'turn_ended' in result and result['turn_ended']:
                    print(f"Turn ended. Next player: {result['next_player']}")
                    if 'new_turn' in result and result['new_turn']:
                        print(f"New turn number: {result['turn_number']}")
    
    # Print final game state overview for each player
    print("\n===== FINAL GAME STATE =====")
    for player in players:
        state = game_manager.get_game_state(game_id, player['id'])
        territory_count = len(state['your_territories'])
        print(f"{player['name']} controls {territory_count} territories")
    
    print("\nGame test completed successfully.")


if __name__ == "__main__":
    main()