import pygame
import sys
import random
import requests
import json
import asyncio

# --- NEW: Force pygbag to package assets ---
# These lines look strange, but they tell the builder to find these files
try:
    import background.png
    import lore.png
    import player_tile.png
    import purple_tile.png
    import red_tile.png
    import roll.png
    import roll_pressed.png
    import Pixele_Unique.ttf
except ImportError:
    pass # This will fail in normal Python, but pygbag will see it
# --- END NEW ---

# Initialize Pygame
pygame.init()

# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 800
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Static Breach - Wide Layout")

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
PURPLE = (128, 0, 128)
RED = (255, 0, 0)
GREEN = (40, 167, 69)
GRAY = (128, 128, 128)
LIGHT_GRAY = (150, 150, 150)
DARK_GRAY = (50, 50, 50)
YELLOW = (255, 193, 7)
LOG_GREEN = (0, 255, 0)

# Fonts
FONT_NAME = 'Pixele_Unique.ttf' # Using the renamed file
font = pygame.font.Font(FONT_NAME, 18)
large_font = pygame.font.Font(FONT_NAME, 28)
title_font = pygame.font.Font(FONT_NAME, 24)
lore_log_font = pygame.font.Font(FONT_NAME, 24)
game_over_font = pygame.font.Font(FONT_NAME, 48)

NUMBER_FONT_NAME = 'Arial'
number_font_small = pygame.font.SysFont(NUMBER_FONT_NAME, 18, bold=True)
number_font_medium = pygame.font.SysFont(NUMBER_FONT_NAME, 24, bold=True)
number_font_large = pygame.font.SysFont(NUMBER_FONT_NAME, 28, bold=True)

# Grid settings
GRID_SIZE = 4
TILE_SIZE = 100
GRID_X = (SCREEN_WIDTH - GRID_SIZE * TILE_SIZE) // 2
GRID_Y = 120
GRID_WIDTH_PX = GRID_SIZE * TILE_SIZE
GRID_HEIGHT_PX = GRID_SIZE * TILE_SIZE

# Player starting position
player_pos = [3, 0] # This is a list [row, col]

# Exit position
exit_pos = [0, 3]

# Dice faces
DICE_FACES = ['1', '2', '3', 'GLITCH', 'BREACH', 'CHRONO']

def submit_score(player_name, score, lore, win):
    url = "https://YOUR_SERVER_URL_HERE.com/submit"
    
    data = {
        "name": player_name,
        "score": score,
        "lore": lore,
        "win": win
    }
    
    try:
        response = requests.post(url, data=json.dumps(data), headers={"Content-Type": "application/json"}, timeout=5)
        
        if response.status_code == 200:
            print("Score submitted successfully!")
            return True
        else:
            print(f"Server returned status: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to server: {e}")
        return False

# Game states
class Game:
    def __init__(self):
        self.signal_strength = 7
        self.chrono = 0
        self.lore = 0
        
        self.game_state = 'playing'
        self.animation_start_time = 0
        self.animation_delay = 50 
        self.animation_step = 0
        self.lore_animation_pos = None
        
        self.player_name = ""
        self.final_score = 0
        self.player_won = False
        
        self.lore_locations = []
        possible_tiles = []
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if [r, c] != player_pos and [r, c] != exit_pos:
                    possible_tiles.append([r, c])
        
        num_lore = random.randint(0, 4)
        self.lore_locations = random.sample(possible_tiles, num_lore)
        
        self.fill_order = []
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                self.fill_order.append([r, c])
        random.shuffle(self.fill_order)
        
        self.grid = [[random.randint(3, 8) for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.breached = [[False for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.breached[player_pos[0]][player_pos[1]] = True
        self.selected_tile = None
        self.dice_results = [None, None]
        self.total_strength = 0
        self.rolled = False
        self.log = ["Game started. Select an adjacent tile and roll!"]

    def is_adjacent(self, row, col):
        pr, pc = player_pos
        return (abs(row - pr) + abs(col - pc) == 1) and not self.breached[row][col]

    def roll_dice(self):
        self.dice_results = [random.choice(DICE_FACES), random.choice(DICE_FACES)]
        self.total_strength = 0
        glitch_count = 0
        chrono_count = 0
        breach_count = 0

        for die in self.dice_results:
            if die in ['1', '2', '3']:
                self.total_strength += int(die)
            elif die == 'BREACH':
                breach_count += 1
            elif die == 'GLITCH':
                glitch_count += 1
            elif die == 'CHRONO':
                chrono_count += 1

        self.total_strength += breach_count * 3
        self.signal_strength -= glitch_count
        self.chrono += chrono_count

        if glitch_count > 0:
            self.log.append(f"Glitch! Lost {glitch_count} health.")
        if chrono_count > 0:
            self.log.append(f"Gained {chrono_count} Chrono.")

        self.rolled = True

    def use_rewind(self, die_index):
        if self.chrono >= 1 and self.rolled:
            self.chrono -= 1
            
            old_die = self.dice_results[die_index]
            if old_die in ['1', '2', '3']:
                self.total_strength -= int(old_die)
            elif old_die == 'BREACH':
                self.total_strength -= 3
            
            new_die = random.choice(DICE_FACES)
            self.dice_results[die_index] = new_die
            
            if new_die in ['1', '2', '3']:
                self.total_strength += int(new_die)
            elif new_die == 'BREACH':
                self.total_strength += 3
            elif new_die == 'GLITCH':
                self.signal_strength -= 1
                self.log.append(f"Rewound into a Glitch! -1 health.")
            elif new_die == 'CHRONO':
                self.chrono += 1
                self.log.append(f"Rewound into Chrono! +1 Chrono.")
            
            self.log.append(f"RE ROLLED die {die_index + 1} to {new_die}.")
            return True
        return False

    def use_overload(self):
        if self.chrono >= 2 and self.rolled:
            self.chrono -= 2
            self.total_strength += 1
            self.log.append("Overloaded: +1 strength.")
            return True
        return False

    def use_skip(self):
        if self.chrono >= 3 and self.selected_tile:
            self.chrono -= 3
            row, col = self.selected_tile
            self.breached[row][col] = True
            
            if [row, col] in self.lore_locations:
                self.game_state = 'lore_animation'
                self.animation_start_time = pygame.time.get_ticks()
                self.lore_animation_pos = [row, col]
                self.log.append("LORE FOUND!")
                self.lore_locations.remove([row, col])
            else:
                player_pos[0], player_pos[1] = row, col
            
            self.log.append("Skipped: Auto-breached tile.")
            self.selected_tile = None
            self.rolled = False
            return True
        return False

    def resolve_breach(self):
        if self.selected_tile and self.rolled:
            row, col = self.selected_tile
            shield = self.grid[row][col]
            if self.total_strength >= shield:
                self.breached[row][col] = True
                
                if [row, col] in self.lore_locations:
                    self.game_state = 'lore_animation'
                    self.animation_start_time = pygame.time.get_ticks()
                    self.lore_animation_pos = [row, col]
                    self.log.append("LORE FOUND!")
                    self.lore_locations.remove([row, col])
                else:
                    player_pos[0], player_pos[1] = row, col
                    
                self.log.append(f"Success! Breached shield {shield} with {self.total_strength}.")
            else:
                self.signal_strength -= 1
                self.log.append(f"Failure. Lost 1 health. Needed {shield}, had {self.total_strength}.")
            
            self.selected_tile = None
            self.rolled = False
            self.dice_results = [None, None]
            
            if self.game_state == 'playing':
                self.check_lose()

    def win_game(self):
        player_pos[:] = exit_pos
        self.game_state = 'win_animation'
        self.animation_start_time = pygame.time.get_ticks()
        self.log = ["SIGNAL BREACH SUCCESS!"]
        self.player_won = True

    def check_lose(self):
        if self.signal_strength <= 0:
            self.game_state = 'lose_animation'
            self.animation_start_time = pygame.time.get_ticks()
            self.animation_step = 0
            self.log = ["GAME OVER!"]
            self.player_won = False
            return True
        return False
        
    def end_game_animation_complete(self):
        self.game_state = 'enter_name'
        self.final_score = (1000 if self.player_won else 0) + (self.lore * 100)
        self.log = ["RESTART GAME"]

# Buttons
class Button:
    def __init__(self, x, y, width, height, text, color=GRAY, text_color=BLACK):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.base_color = color
        self.disabled_color = DARK_GRAY
        self.text_color = text_color
    
    def draw(self, surface, disabled=False):
        color = self.disabled_color if disabled else self.base_color
        pygame.draw.rect(surface, color, self.rect, border_radius=5)
        
        if self.text_color == WHITE:
            text_color = WHITE
        else:
            text_color = self.text_color if not disabled else GRAY
        
        text_surf = font.render(self.text, True, text_color)
        
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

async def main():
    game = Game()
    
    background_image = pygame.image.load("background.png").convert()
    
    red_tile_img = pygame.image.load("red_tile.png").convert()
    purple_tile_img = pygame.image.load("purple_tile.png").convert()
    player_tile_img = pygame.image.load("player_tile.png").convert_alpha()
    lore_img = pygame.image.load("lore.png").convert_alpha()
    
    roll_button_img = pygame.image.load("roll.png").convert_alpha()
    roll_pressed_img = pygame.image.load("roll_pressed.png").convert_alpha()
    roll_button_pressed = False

    UI_PADDING = 20
    BUTTON_WIDTH = 140
    BUTTON_HEIGHT = 45
    GRID_CENTER_X = GRID_X + (GRID_WIDTH_PX // 2)
    
    LEFT_COL_X = (GRID_X - BUTTON_WIDTH) // 2
    LEFT_COL_Y_START = 300
    Y_SPACING = 60

    RIGHT_COL_X = GRID_X + GRID_WIDTH_PX + (GRID_X - BUTTON_WIDTH) // 2
    
    reroll1_button = Button(LEFT_COL_X, LEFT_COL_Y_START, BUTTON_WIDTH, BUTTON_HEIGHT, "RE ROLL 1 (1C)", YELLOW, text_color=WHITE)
    reroll2_button = Button(LEFT_COL_X, LEFT_COL_Y_START + Y_SPACING, BUTTON_WIDTH, BUTTON_HEIGHT, "RE ROLL 2 (1C)", YELLOW, text_color=WHITE)
    overload_button = Button(LEFT_COL_X, LEFT_COL_Y_START + (2 * Y_SPACING), BUTTON_WIDTH, BUTTON_HEIGHT, "OVERLOAD (2C)", YELLOW, text_color=WHITE)
    skip_button = Button(LEFT_COL_X, LEFT_COL_Y_START + (3 * Y_SPACING), BUTTON_WIDTH, BUTTON_HEIGHT, "SKIP (3C)", YELLOW, text_color=WHITE)

    roll_button_rect = pygame.Rect(RIGHT_COL_X, 330, 140, 50)
    resolve_button = Button(RIGHT_COL_X, 330 + Y_SPACING, BUTTON_WIDTH, BUTTON_HEIGHT, "RESOLVE", GREEN, text_color=WHITE)

    restart_text_rect = None

    running = True
    while running:
        game_over = game.game_state in ['win_animation', 'lose_animation', 'enter_name']
        current_time = pygame.time.get_ticks()
        
        events = pygame.event.get()
        
        if game.game_state == 'lore_animation':
            if current_time - game.animation_start_time > 3000:
                game.game_state = 'playing'
                player_pos[:] = game.lore_animation_pos
                game.lore += 1
                game.lore_animation_pos = None
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
        
        elif game.game_state == 'lose_animation':
            if current_time - game.animation_start_time > game.animation_delay and game.animation_step < (GRID_SIZE * GRID_SIZE):
                game.animation_step += 1
                game.animation_start_time = current_time
            elif game.animation_step >= (GRID_SIZE * GRID_SIZE) and current_time - game.animation_start_time > 2000:
                game.end_game_animation_complete()
                
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
        
        elif game.game_state == 'win_animation':
            if current_time - game.animation_start_time > 3000:
                game.end_game_animation_complete()
            
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
        
        screen.blit(background_image, (0, 0))

        # --- Draw grid ---
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                x = GRID_X + col * TILE_SIZE
                y = GRID_Y + row * TILE_SIZE
                current_tile_pos = [row, col]
                
                if current_tile_pos == exit_pos:
                    screen.blit(red_tile_img, (x, y))
                elif current_tile_pos == player_pos:
                    screen.blit(player_tile_img, (x, y))
                elif game.breached[row][col]:
                    pygame.draw.rect(screen, BLACK, (x, y, TILE_SIZE, TILE_SIZE))
                else:
                    screen.blit(purple_tile_img, (x, y))
                
                if not game.breached[row][col] and current_tile_pos != exit_pos:
                    shield_text_shadow = number_font_small.render(str(game.grid[row][col]), True, BLACK)
                    shield_text = number_font_small.render(str(game.grid[row][col]), True, WHITE)
                    shield_rect_shadow = shield_text_shadow.get_rect(center=(x + TILE_SIZE // 2 + 1, y + TILE_SIZE // 2 + 1))
                    shield_rect = shield_text.get_rect(center=(x + TILE_SIZE // 2, y + TILE_SIZE // 2))
                    screen.blit(shield_text_shadow, shield_rect_shadow)
                    screen.blit(shield_text, shield_rect)
                
                pygame.draw.rect(screen, WHITE, (x, y, TILE_SIZE, TILE_SIZE), 2)
        # --- END grid ---
        
        if game.game_state == 'lore_animation':
            flash_on = (current_time // 250) % 2 == 0
            x = GRID_X + game.lore_animation_pos[1] * TILE_SIZE
            y = GRID_Y + game.lore_animation_pos[0] * TILE_SIZE
            if flash_on:
                screen.blit(lore_img, (x, y))
            else:
                screen.blit(player_tile_img, (x, y))
        
        elif game.game_state == 'win_animation':
            flash_on = (current_time // 250) % 2 == 0
            x = GRID_X + exit_pos[1] * TILE_SIZE
            y = GRID_Y + exit_pos[0] * TILE_SIZE
            if flash_on:
                screen.blit(player_tile_img, (x, y))
            else:
                screen.blit(red_tile_img, (x, y))
                
        elif game.game_state == 'lose_animation':
            for i in range(game.animation_step):
                r, c = game.fill_order[i]
                x = GRID_X + c * TILE_SIZE
                y = GRID_Y + r * TILE_SIZE
                screen.blit(red_tile_img, (x, y))
            
            if game.animation_step >= (GRID_SIZE * GRID_SIZE):
                flash_on = (current_time // 250) % 2 == 0
                if flash_on:
                    s = pygame.Surface((GRID_WIDTH_PX, GRID_HEIGHT_PX))
                    s.set_alpha(128)
                    s.fill(RED)
                    screen.blit(s, (GRID_X, GRID_Y))

        if game.selected_tile:
            row, col = game.selected_tile
            x = GRID_X + col * TILE_SIZE
            y = GRID_Y + row * TILE_SIZE
            pygame.draw.rect(screen, YELLOW, (x, y, TILE_SIZE, TILE_SIZE), 4)

        # --- Draw UI ---
        
        health_title = title_font.render("SIGNAL STRENGTH", True, BLACK)
        health_title_x = LEFT_COL_X + 20
        screen.blit(health_title, (health_title_x, 50))
        SQUARE_SIZE = 15
        PADDING = 5
        MAX_HEALTH = 7
        BAR_START_X = health_title_x
        BAR_START_Y = 50 + title_font.get_height() + 5
        BAR_HEIGHT = SQUARE_SIZE + (PADDING * 2)
        BAR_WIDTH = (MAX_HEALTH * (SQUARE_SIZE + PADDING)) + PADDING
        pygame.draw.rect(screen, BLACK, (BAR_START_X, BAR_START_Y, BAR_WIDTH, BAR_HEIGHT), border_radius=5)
        for i in range(game.signal_strength):
            sq_x = BAR_START_X + PADDING + i * (SQUARE_SIZE + PADDING)
            sq_y = BAR_START_Y + PADDING
            pygame.draw.rect(screen, RED, (sq_x, sq_y, SQUARE_SIZE, SQUARE_SIZE))

        chrono_text = number_font_large.render(f"Chrono: {game.chrono}", True, WHITE)
        chrono_rect = chrono_text.get_rect(right=RIGHT_COL_X + BUTTON_WIDTH - 30, top=60) 
        chrono_box_rect = chrono_rect.inflate(20, 10)
        pygame.draw.rect(screen, BLACK, chrono_box_rect, border_radius=5)
        screen.blit(chrono_text, chrono_rect)

        lore_text = number_font_large.render(f"Lore: {game.lore}", True, YELLOW)
        lore_rect = lore_text.get_rect(centerx=GRID_CENTER_X, top=60)
        lore_box_rect = lore_rect.inflate(20, 10)
        pygame.draw.rect(screen, BLACK, lore_box_rect, border_radius=5)
        screen.blit(lore_text, lore_rect)

        ability_title = font.render("Chrono Abilities", True, YELLOW)
        ability_title_rect = ability_title.get_rect(topleft=(LEFT_COL_X, LEFT_COL_Y_START - 40))
        ability_title_box = ability_title_rect.inflate(20, 10)
        pygame.draw.rect(screen, BLACK, ability_title_box, border_radius=5)
        screen.blit(ability_title, ability_title_rect)
        reroll1_button.draw(screen, disabled=(game.chrono < 1 or not game.rolled or game_over))
        reroll2_button.draw(screen, disabled=(game.chrono < 1 or not game.rolled or game_over))
        overload_button.draw(screen, disabled=(game.chrono < 2 or not game.rolled or game_over))
        skip_button.draw(screen, disabled=(game.chrono < 3 or not game.selected_tile or game.rolled or game_over))

        dice_box_rect = pygame.Rect(RIGHT_COL_X - 10, 145, BUTTON_WIDTH + 20, 175)
        pygame.draw.rect(screen, BLACK, dice_box_rect, border_radius=5)
        dice_title = number_font_medium.render("Dice Results", True, WHITE)
        screen.blit(dice_title, (RIGHT_COL_X, 150))
        d1_label = number_font_small.render("DICE 1", True, WHITE)
        screen.blit(d1_label, (RIGHT_COL_X, 180))
        d1_text_str = game.dice_results[0] if game.dice_results[0] else "--"
        d1_text = number_font_large.render(d1_text_str, True, WHITE)
        screen.blit(d1_text, (RIGHT_COL_X + 20, 200))
        d2_label = number_font_small.render("DICE 2", True, WHITE)
        screen.blit(d2_label, (RIGHT_COL_X, 230))
        d2_text_str = game.dice_results[1] if game.dice_results[1] else "--"
        d2_text = number_font_large.render(d2_text_str, True, WHITE)
        screen.blit(d2_text, (RIGHT_COL_X + 20, 250))
        strength_text = number_font_large.render(f"Strength: {game.total_strength}", True, WHITE)
        screen.blit(strength_text, (RIGHT_COL_X, 280))
        roll_disabled = (not game.selected_tile or game.rolled or game_over)
        if not roll_disabled and roll_button_pressed:
            screen.blit(roll_pressed_img, roll_button_rect.topleft)
        else:
            screen.blit(roll_button_img, roll_button_rect.topleft)
        resolve_button.draw(screen, disabled=(not game.rolled or game_over))

        # --- Centered Log with Box ---
        log_y_start = 580
        log_line_height = 22
        num_log_lines = 5
        num_visual_lines = 6
        log_box_width = 500
        log_box_height = (num_visual_lines * log_line_height) + 10
        log_box_x = GRID_CENTER_X - (log_box_width // 2)
        log_box_y = log_y_start - 5
        log_box_rect = pygame.Rect(log_box_x, log_box_y, log_box_width, log_box_height)
        pygame.draw.rect(screen, BLACK, log_box_rect, border_radius=5)
        
        restart_y = log_y_start + log_box_height - log_line_height - 5
        restart_text_surf = font.render("RESTART GAME", True, LOG_GREEN)
        restart_text_rect = restart_text_surf.get_rect(centerx=GRID_CENTER_X, top=restart_y)
            
        if game.game_state == 'enter_name':
            enter_text = game_over_font.render("ENTER NAME:", True, LOG_GREEN)
            enter_rect = enter_text.get_rect(centerx=GRID_CENTER_X, top=log_y_start + 10)
            screen.blit(enter_text, enter_rect)
            
            name_text = game_over_font.render(game.player_name, True, WHITE)
            name_rect = name_text.get_rect(centerx=GRID_CENTER_X, top=enter_rect.bottom + 10)
            screen.blit(name_text, name_rect)
            
            if (current_time // 500) % 2 == 0:
                cursor_rect = pygame.Rect(name_rect.right, name_rect.top, 5, name_rect.height)
                pygame.draw.rect(screen, WHITE, cursor_rect)
            
            screen.blit(restart_text_surf, restart_text_rect)
            
        elif game_over:
            log_text_surf = game_over_font.render(game.log[0], True, LOG_GREEN)
            log_text_rect = log_text_surf.get_rect(centerx=GRID_CENTER_X, top=log_y_start + 30)
            screen.blit(log_text_surf, log_text_rect)
            
        else: # Regular log
            log_y = log_y_start
            for msg in game.log[-num_log_lines:]:
                if msg == "LORE FOUND!":
                    log_text = lore_log_font.render(msg, True, LOG_GREEN)
                else:
                    log_text = font.render(msg, True, LOG_GREEN)
                
                text_width = log_text.get_width()
                log_x = GRID_CENTER_X - (text_width // 2)
                screen.blit(log_text, (log_x, log_y))
                log_y += log_line_height
        # --- END Log ---

        # Event handling
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            
            if game.game_state == 'enter_name':
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if len(game.player_name) > 0:
                            submit_score(game.player_name, game.final_score, game.lore, game.player_won)
                            player_pos[:] = [3, 0]
                            game = Game()
                    elif event.key == pygame.K_BACKSPACE:
                        game.player_name = game.player_name[:-1]
                    elif len(game.player_name) < 10:
                        game.player_name += event.unicode
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    pos = pygame.mouse.get_pos()
                    if restart_text_rect and restart_text_rect.collidepoint(pos):
                        player_pos[:] = [3, 0]
                        game = Game()
            
            elif game.game_state == 'playing':
                if event.type == pygame.MOUSEBUTTONDOWN:
                    pos = pygame.mouse.get_pos()

                    if not game_over:
                        if GRID_X <= pos[0] < GRID_X + GRID_WIDTH_PX and \
                           GRID_Y <= pos[1] < GRID_Y + GRID_HEIGHT_PX:
                            
                            col = (pos[0] - GRID_X) // TILE_SIZE
                            row = (pos[1] - GRID_Y) // TILE_SIZE
                            
                            if [row, col] == exit_pos:
                                pr, pc = player_pos
                                if (abs(row - pr) + abs(col - pc) == 1):
                                    game.win_game()
                                    continue
                            
                            if game.is_adjacent(row, col):
                                game.selected_tile = [row, col]
                                game.log.append(f"Selected tile ({row}, {col}) with shield {game.grid[row][col]}")
                        else:
                            roll_disabled = (not game.selected_tile or game.rolled or game_over)
                            if roll_button_rect.collidepoint(pos) and not roll_disabled:
                                roll_button_pressed = True
                            
                            elif resolve_button.is_clicked(pos) and game.rolled:
                                game.resolve_breach()
                            elif reroll1_button.is_clicked(pos):
                                game.use_rewind(0)
                            elif reroll2_button.is_clicked(pos):
                                game.use_rewind(1)
                            elif overload_button.is_clicked(pos):
                                game.use_overload()
                            elif skip_button.is_clicked(pos) and game.selected_tile and not game.rolled:
                                game.use_skip()

                elif event.type == pygame.MOUSEBUTTONUP:
                    if not game_over:
                        if roll_button_pressed:
                            roll_button_pressed = False
                            pos = pygame.mouse.get_pos()
                            if roll_button_rect.collidepoint(pos):
                                game.roll_dice()

        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    asyncio.run(main())