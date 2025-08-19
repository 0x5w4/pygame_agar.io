import socket
import threading
import pickle
import time
import random
import math

class GameServer:
    """
    Manages the game state, player connections, and all server-side logic.
    """
    # --- Constants ---
    HOST = '0.0.0.0'  # Bind to all available network interfaces
    PORT = 5555
    BUFFER_SIZE = 4096

    # --- Game Settings ---
    W, H = 850, 720
    START_RADIUS = 7
    ROUND_TIME = 60 * 5  # 5 minutes
    MASS_LOSS_TIME = 7
    COLORS = [
        (255,0,0), (255,128,0), (255,255,0), (128,255,0), (0,255,0),
        (0,255,128), (0,255,255), (0,128,255), (0,0,255), (128,0,255),
        (255,0,255), (255,0,128), (128,128,128), (0,0,0)
    ]

    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # --- Game State ---
        self.players = {}
        self.balls = []
        self.msg_history = []
        self.game_time = "Starting Soon"
        self.start_time = 0
        self.game_started = False
        self.next_mass_loss_tick = 1
        self.player_id_counter = 0
        
        # --- Threading Safety ---
        # A lock is crucial to prevent race conditions when multiple threads
        # access shared data like `self.players` or `self.balls`.
        self.lock = threading.Lock()

    def start(self):
        """Binds the server and starts listening for connections."""
        try:
            self.server_socket.bind((self.HOST, self.PORT))
        except socket.error as e:
            print(f"[ERROR] Server could not start: {e}")
            quit()

        self.server_socket.listen(5)
        server_ip = socket.gethostbyname(socket.gethostname())
        print(f"[SERVER] Server Started. Listening on {server_ip}:{self.PORT}")

        self._create_balls(200)
        print("[GAME] World generated. Waiting for players...")

        # Main loop to accept new connections
        while True:
            client_socket, client_address = self.server_socket.accept()
            print(f"[CONNECTION] Connected to: {client_address}")

            if not self.game_started:
                self.start_time = time.time()
                self.game_started = True
                print("[GAME] First player joined. Game timer started!")

            # Assign a unique ID to the new player
            current_id = self.player_id_counter
            self.player_id_counter += 1

            # Create a new thread for each client
            thread = threading.Thread(target=self._handle_client, args=(client_socket, current_id))
            thread.daemon = True # Allows main program to exit even if threads are running
            thread.start()

    def _create_balls(self, n):
        """Creates n new food balls in random locations."""
        for _ in range(n):
            while True:
                is_safe_location = True
                x = random.randrange(0, self.W)
                y = random.randrange(0, self.H)
                # Ensure balls don't spawn on top of players
                for player in self.players.values():
                    dist = math.hypot(x - player["x"], y - player["y"])
                    if dist <= self.START_RADIUS + player["score"]:
                        is_safe_location = False
                        break
                if is_safe_location:
                    break
            self.balls.append((x, y, random.choice(self.COLORS)))

    def _get_start_location(self):
        """Finds a safe starting location for a new player."""
        while True:
            is_safe_location = True
            x = random.randrange(0, self.W)
            y = random.randrange(0, self.H)
            for player in self.players.values():
                dist = math.hypot(x - player["x"], y - player["y"])
                if dist <= self.START_RADIUS + player["score"]:
                    is_safe_location = False
                    break
            if is_safe_location:
                return (x, y)

    def _update_game_state(self):
        """Periodically updates game-wide state like the timer and mass loss."""
        if not self.game_started:
            return

        elapsed_time = time.time() - self.start_time
        self.game_time = round(elapsed_time)

        if self.game_time >= self.ROUND_TIME:
            self.game_started = False # Reset game logic can be added here
        
        # Mass loss check
        if self.game_time // self.MASS_LOSS_TIME == self.next_mass_loss_tick:
            self.next_mass_loss_tick += 1
            for player in self.players.values():
                if player["score"] > 8:
                    player["score"] = math.floor(player["score"] * 0.95)

    def _check_collisions(self, current_id):
        """Checks for and handles collisions for a given player."""
        player = self.players[current_id]
        px, py, p_score = player["x"], player["y"], player["score"]

        # 1. Player vs. Balls
        for ball in self.balls[:]: # Iterate over a copy
            bx, by, _ = ball
            dist = math.hypot(px - bx, py - by)
            if dist <= self.START_RADIUS + p_score:
                player["score"] += 0.5
                self.balls.remove(ball)

        # 2. Player vs. Player
        for other_id, other_player in self.players.items():
            if current_id == other_id:
                continue

            opx, opy, op_score = other_player["x"], other_player["y"], other_player["score"]
            dist = math.hypot(px - opx, py - opy)

            # Check if one player can eat the other
            if p_score > op_score * 1.15 and dist < self.START_RADIUS + p_score:
                player["score"] = math.sqrt(p_score**2 + op_score**2)
                other_player["score"] = 0
                other_player["x"], other_player["y"] = self._get_start_location()
                print(f"[GAME] {player['name']} ATE {other_player['name']}")
    
    def _add_chat_message(self, message):
        """Adds a message to the chat history, trimming old messages."""
        self.msg_history.append(message)
        if len(self.msg_history) > 20:
            self.msg_history.pop(0)

    def _handle_client(self, client_socket, current_id):
        """Handles all communication with a single client."""
        try:
            # 1. Initial Handshake
            username = client_socket.recv(1024).decode("utf-8")
            print(f"[LOG] {username} has connected with ID {current_id}.")
            
            with self.lock:
                self._add_chat_message(f"{username} CONNECTED")
                start_pos = self._get_start_location()
                color = self.COLORS[current_id % len(self.COLORS)]
                self.players[current_id] = {
                    "x": start_pos[0], "y": start_pos[1],
                    "color": color, "score": 0, "name": username
                }

            # WARNING: Using pickle is a security risk. A malicious client could
            # send crafted data to execute code on your server.
            # For a simple project it's okay, but for production, use JSON or a safer protocol.
            client_socket.send(pickle.dumps(current_id))

            # 2. Main Communication Loop
            while True:
                data = client_socket.recv(self.BUFFER_SIZE)
                if not data:
                    break
                
                # The received data is a command string, e.g., "move 100 200"
                command = pickle.loads(data)
                
                send_data = None
                with self.lock:
                    self._update_game_state()

                    if command.startswith("move"):
                        _, x, y = command.split()
                        self.players[current_id]["x"] = int(x)
                        self.players[current_id]["y"] = int(y)
                        
                        if self.game_started:
                            self._check_collisions(current_id)
                        
                        if len(self.balls) < 150:
                            self._create_balls(random.randrange(50, 100))
                            
                    elif command.startswith("msg"):
                        msg = f"{self.players[current_id]['name']}: {command[4:]}"
                        self._add_chat_message(msg)

                    # Always package the full game state to send back
                    send_data = (self.balls, self.players, self.game_time, self.msg_history)
                
                client_socket.send(pickle.dumps(send_data))

        except (socket.error, ConnectionResetError, EOFError, pickle.UnpicklingError) as e:
            print(f"[ERROR] Client {current_id} error: {e}")
        finally:
            # 3. Cleanup on Disconnect
            with self.lock:
                if current_id in self.players:
                    username = self.players[current_id]["name"]
                    print(f"[DISCONNECT] {username} has disconnected.")
                    self._add_chat_message(f"{username} DISCONNECTED")
                    del self.players[current_id]
            client_socket.close()

if __name__ == "__main__":
    server = GameServer()
    server.start()