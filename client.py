import pygame
import socket
import pickle
import time
import math
import os

class UIManager:
    """Manages all UI elements, with robust text wrapping."""
    def __init__(self, width, height):
        self.width, self.height = width, height
        font_path = os.path.join('assets', 'Dosis-Bold.ttf')
        
        try:
            self.font_sm = pygame.font.Font(font_path, 16)
            self.font_md = pygame.font.Font(font_path, 22)
            self.font_lg = pygame.font.Font(font_path, 48)
        except pygame.error:
            print(f"Font not found at {font_path}. Using default font.")
            self.font_sm = pygame.font.SysFont("Arial", 16)
            self.font_md = pygame.font.SysFont("Arial", 22)
            self.font_lg = pygame.font.SysFont("Arial", 48)

        self.colors = {
            'bg_dark': (20, 25, 35),
            'panel_bg': (30, 35, 45, 150),
            'text': (230, 230, 240),
            'text_muted': (150, 150, 160),
            'accent': (0, 150, 255)
        }
        
        self.chat_history_surfaces = []

    def _wrap_text(self, text, font, max_width):
        """Wraps text, breaking both spaces and long words."""
        lines = []
        words = text.split(' ')
        current_line = ""

        for word in words:
            # Handle words that are longer than the line itself
            if font.size(word)[0] > max_width:
                if current_line: # Finalize the line before the long word
                    lines.append(current_line.strip())
                
                # Break the long word character by character
                long_word_buffer = ""
                for char in word:
                    if font.size(long_word_buffer + char)[0] < max_width:
                        long_word_buffer += char
                    else:
                        lines.append(long_word_buffer)
                        long_word_buffer = char
                current_line = long_word_buffer + " " # The remainder becomes the new line start

            # Normal word wrapping
            elif font.size(current_line + word)[0] < max_width:
                current_line += word + " "
            else:
                lines.append(current_line.strip())
                current_line = word + " "
        
        if current_line.strip():
            lines.append(current_line.strip())

        return [font.render(line, True, self.colors['text']) for line in lines if line]

    def _create_panel(self, rect):
        """Creates a styled, rounded panel surface."""
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, self.colors['panel_bg'], panel.get_rect(), border_radius=12)
        pygame.draw.rect(panel, (*self.colors['accent'], 180), panel.get_rect(), 2, border_radius=12)
        return panel

    def draw_start_menu(self, win, username):
        win.fill(self.colors['bg_dark'])
        title_text = self.font_lg.render("AGAR.IO CLONE", True, self.colors['text'])
        win.blit(title_text, (self.width / 2 - title_text.get_width() / 2, 200))
        input_box = pygame.Rect(self.width / 2 - 175, 320, 350, 50)
        pygame.draw.rect(win, (40, 45, 55), input_box, border_radius=8)
        pygame.draw.rect(win, self.colors['accent'], input_box, 2, border_radius=8)
        input_text = self.font_md.render(username, True, self.colors['text'])
        win.blit(input_text, (input_box.x + 15, input_box.y + 10))
        prompt_text = self.font_sm.render("Enter Your Name and Press ENTER", True, self.colors['text_muted'])
        win.blit(prompt_text, (self.width / 2 - prompt_text.get_width() / 2, 390))
        pygame.display.update()

    def update_chat_history(self, msg_history):
        self.chat_history_surfaces = []
        chat_panel_width = 350 - 30 
        for msg in msg_history:
            wrapped_surfaces = self._wrap_text(msg, self.font_sm, chat_panel_width)
            self.chat_history_surfaces.extend(wrapped_surfaces)

    def draw_hud(self, win, players, player_id, is_chatting, chat_input, fps):
        # Leaderboard
        panel_rect = pygame.Rect(self.width - 210, 10, 200, 170)
        win.blit(self._create_panel(panel_rect), panel_rect.topleft)
        title = self.font_md.render("LEADERBOARD", True, self.colors['text'])
        title_x = panel_rect.x + (panel_rect.width - title.get_width()) / 2
        win.blit(title, (title_x, panel_rect.y + 10))
        sorted_players = sorted(players.values(), key=lambda p: p['score'], reverse=True)[:5]
        for i, p in enumerate(sorted_players):
            name = self.font_sm.render(f"{i+1}. {p['name']}", True, self.colors['text_muted'])
            score = self.font_sm.render(str(int(p['score'])), True, self.colors['text'])
            win.blit(name, (panel_rect.x + 15, panel_rect.y + 55 + i * 22))
            win.blit(score, (panel_rect.right - score.get_width() - 15, panel_rect.y + 55 + i * 22))

        # Chat
        chat_rect = pygame.Rect(10, self.height - 220, 350, 210)
        win.blit(self._create_panel(chat_rect), chat_rect.topleft)
        chat_title = self.font_md.render("CHAT", True, self.colors['text'])
        chat_title_x = chat_rect.x + (chat_rect.width - chat_title.get_width()) / 2
        win.blit(chat_title, (chat_title_x, chat_rect.y + 10))
        for i, surface in enumerate(self.chat_history_surfaces[-7:]):
            win.blit(surface, (chat_rect.x + 15, chat_rect.y + 55 + i * 20))
        if is_chatting:
            input_rect = pygame.Rect(chat_rect.x, chat_rect.bottom - 35, chat_rect.width, 30)
            pygame.draw.rect(win, (40, 45, 55), input_rect, border_radius=8)
            prompt = f"> {chat_input}"
            if time.time() % 1 > 0.5: prompt += "_"
            input_surf = self.font_sm.render(prompt, True, self.colors['text'])
            win.blit(input_surf, (input_rect.x + 10, input_rect.y + 5))
            
        # Player Stats & FPS
        player = players.get(player_id)
        stats_text = f"Mass: {int(player['score']) if player else 0}"
        fps_text = f"FPS: {fps:.0f}"
        stats_surf = self.font_md.render(stats_text, True, self.colors['text'])
        fps_surf = self.font_md.render(fps_text, True, self.colors['text_muted'])
        stats_panel_rect = pygame.Rect(10, 10, max(stats_surf.get_width(), fps_surf.get_width()) + 30, 70)
        win.blit(self._create_panel(stats_panel_rect), stats_panel_rect.topleft)
        win.blit(stats_surf, (stats_panel_rect.x + 15, stats_panel_rect.y + 10))
        win.blit(fps_surf, (stats_panel_rect.x + 15, stats_panel_rect.y + 38))
        
    def draw_minimap(self, win, players, player_id, world_size):
        map_size = 150
        map_rect = pygame.Rect(self.width - map_size - 10, self.height - map_size - 10, map_size, map_size)
        win.blit(self._create_panel(map_rect), map_rect.topleft)
        W, H = world_size
        for p_id, p in players.items():
            map_x = int(p['x'] / W * map_size)
            map_y = int(p['y'] / H * map_size)
            color = self.colors['accent'] if p_id == player_id else p['color']
            pygame.draw.circle(win, color, (map_rect.x + map_x, map_rect.y + map_y), 3)

class GameClient:
    WIDTH, HEIGHT = 1280, 720
    SERVER_IP = "127.0.0.1"
    PORT = 5555
    START_RADIUS = 7

    def __init__(self):
        pygame.init()
        self.win = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("Advanced Agar.io Clone")
        self.clock = pygame.time.Clock()
        self.font_name = pygame.font.SysFont("Arial", 18)
        self.ui = UIManager(self.WIDTH, self.HEIGHT)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.username, self.player_id = "", -1
        self.players, self.balls = {}, []
        self.chat_input, self.is_chatting = "", False
        self.world_size = (850, 720) # Match server's W, H

    def send(self, data):
        try:
            self.client_socket.send(pickle.dumps(data))
            response = self.client_socket.recv(4096 * 2)
            return pickle.loads(response)
        except (socket.error, EOFError, pickle.UnpicklingError):
            return None

    def draw_game_world(self):
        self.win.fill(self.ui.colors['bg_dark'])
        current_player = self.players.get(self.player_id)
        cam_x, cam_y = 0, 0
        if current_player:
            cam_x = current_player["x"] - self.WIDTH / 2
            cam_y = current_player["y"] - self.HEIGHT / 2

        for ball in self.balls:
            bx, by, b_color = ball
            pygame.draw.circle(self.win, b_color, (bx - cam_x, by - cam_y), 5)

        for p in sorted(self.players.values(), key=lambda item: item['score']):
            px, py = p["x"] - cam_x, p["y"] - cam_y
            radius = self.START_RADIUS + p["score"]
            pygame.draw.circle(self.win, p["color"], (px, py), int(radius))
            name_text = self.font_name.render(p["name"], True, self.ui.colors['text'])
            self.win.blit(name_text, (px - name_text.get_width()/2, py - name_text.get_height()/2))
        
        self.ui.draw_hud(self.win, self.players, self.player_id, self.is_chatting, self.chat_input, self.clock.get_fps())
        self.ui.draw_minimap(self.win, self.players, self.player_id, self.world_size)
        pygame.display.update()

    def run(self):
        menu_running = True
        while menu_running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN and len(self.username) > 2: menu_running = False
                    elif event.key == pygame.K_BACKSPACE: self.username = self.username[:-1]
                    elif len(self.username) < 15: self.username += event.unicode
            self.ui.draw_start_menu(self.win, self.username)
            
        try:
            self.client_socket.connect((self.SERVER_IP, self.PORT))
            self.client_socket.send(self.username.encode("utf-8"))
            self.player_id = pickle.loads(self.client_socket.recv(1024))
        except socket.error as e:
            print(f"[CONNECTION FAILED] {e}"); pygame.quit(); return
            
        initial_data = self.send("move 0 0")
        if not initial_data: pygame.quit(); return
        
        self.balls, self.players, _, msg_history = initial_data
        self.ui.update_chat_history(msg_history)

        game_running = True
        while game_running:
            self.clock.tick(60)

            for event in pygame.event.get():
                if event.type == pygame.QUIT: game_running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.is_chatting = not self.is_chatting
                        if not self.is_chatting and self.chat_input:
                            self.send(f"msg {self.chat_input}"); self.chat_input = ""
                    elif self.is_chatting:
                        if event.key == pygame.K_BACKSPACE: self.chat_input = self.chat_input[:-1]
                        else: self.chat_input += event.unicode

            current_player = self.players.get(self.player_id)
            if not self.is_chatting and current_player:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                cam_x, cam_y = current_player["x"] - self.WIDTH / 2, current_player["y"] - self.HEIGHT / 2
                world_mouse_x, world_mouse_y = mouse_x + cam_x, mouse_y + cam_y
                dx, dy = world_mouse_x - current_player["x"], world_mouse_y - current_player["y"]
                dist = math.hypot(dx, dy)
                if dist > 1:
                    speed = max(2, 6 - (current_player["score"] / 20))
                    current_player["x"] += (dx / dist) * speed
                    current_player["y"] += (dy / dist) * speed

                    # --- NEW: WORLD BOUNDARY CHECK ---
                    radius = self.START_RADIUS + current_player["score"]
                    world_w, world_h = self.world_size
                    current_player["x"] = max(radius, min(current_player["x"], world_w - radius))
                    current_player["y"] = max(radius, min(current_player["y"], world_h - radius))

            if current_player:
                response = self.send(f"move {int(current_player['x'])} {int(current_player['y'])}")
                if response:
                    self.balls, self.players, _, msg_history = response
                    if len(msg_history) > len(self.ui.chat_history_surfaces):
                        self.ui.update_chat_history(msg_history)
                else: game_running = False

            self.draw_game_world()

        self.client_socket.close()
        pygame.quit()

if __name__ == "__main__":
    client = GameClient()
    client.run()