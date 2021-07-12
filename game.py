import socket
import pickle
import threading
import contextlib
with contextlib.redirect_stdout(None):
	import pygame
from client import Network
import random
import os

pygame.font.init()

PLAYER_RADIUS = 10
START_VEL = 9
BALL_RADIUS = 5
FONT = "CascadiaCode.ttf"
TITLE = "Jello Battle Royale"

INNER_WIDTH = 850
INNER_HEIGHT = 700
OUTER_WIDTH = 1200
OUTER_HEIGHT = 700

COLORS = [(255,0,0),
		(255,128,0), 
		(255,255,0), 
		(128,255,0),
		(0,255,0),
		(0,255,128),
		(0,255,255),
		(0,128,255),
		(0,0,255), 
		(0,0,255), 
		(128,0,255),
		(255,0,255),
		(255,0,128),
		(128,128,128),
		(0,0,0)]

players = {}
balls = []
msg_history = []

clock = pygame.time.Clock()
base_font = pygame.font.SysFont(FONT, 22)
window = pygame.display.set_mode((OUTER_WIDTH,OUTER_HEIGHT))
title = pygame.display.set_caption(TITLE)

# FUNCTIONS KONVERSI TIME UNTUK MENGUBAH WAKTU DARI SECOND KE MINUTES
def convert_time(t):
	if type(t) == str:
		return t

	if int(t) < 60:
		return str(t) + "s"
	else:
		minutes = str(t // 60)
		seconds = str(t % 60)

		if int(seconds) < 10:
			seconds = "0" + seconds

		return minutes + ":" + seconds

#FUNGSI UNTUK DRAW TIAP FRAME
def redraw_window(players, balls, game_time, score):
	window.fill((255,255,255)) # fill screen white, to clear old frames
	
		# draw all the orbs/balls
	for ball in balls:
		pygame.draw.circle(window, ball[2], (ball[0], ball[1]), BALL_RADIUS)

	# draw each player in the list
	for player in sorted(players, key=lambda x: players[x]["score"]):
		p = players[player]
		pygame.draw.circle(window, p["color"], (p["x"], p["y"]), PLAYER_RADIUS + round(p["score"]))
		# render and draw name for each player
		text = base_font.render(p["name"], True, (0,0,0))
		window.blit(text, (p["x"] - text.get_width()/2, p["y"] - text.get_height()/2))

	# draw scoreboard
	sort_players = list(reversed(sorted(players, key=lambda x: players[x]["score"])))
	title = base_font.render("Scoreboard:", True, (0,0,0))
	start_y = 25
	x = INNER_WIDTH - title.get_width() - 10
	window.blit(title, (x, 5))

	ran = min(len(players), 3)
	for count, i in enumerate(sort_players[:ran]):
		text = base_font.render(str(count+1) + ". " + str(players[i]["name"]), True, (0,0,0))
		window.blit(text, (x, start_y + count * 20))

	# draw time
	text = base_font.render("Time: " + convert_time(game_time), True, (0,0,0))
	window.blit(text,(10,10))
	# draw score
	text = base_font.render("Score: " + str(round(score)),True,(0,0,0))
	window.blit(text,(10,15 + text.get_height()))
	
	text = base_font.render("Message History: ", True, (0,0,0))
	window.blit(text,(860,5))

	text = base_font.render("Send Message: ", True, (0,0,0))
	window.blit(text,(860,630))

#FUNGSI MAIN UNTUK RUN GAMENYA
def main(name):

	global players
	global msg_history
	user_msg = ""

	history_rect = pygame.Rect(INNER_WIDTH + 10,25,140,600)
	input_rect = pygame.Rect(INNER_WIDTH + 10,650,140,25)
	color_passive = pygame.Color('gray')
	color_active = pygame.Color('black')
	color_warning = pygame.Color('red')
	color = color_passive

	rect_status = 1


	# Connect ke server
	server = Network()
	current_id = server.connect(name)

	balls, players, game_time = server.send("get")

	run = True
	while run:
		clock.tick(30) # 30 fps max
		player = players[current_id]
		vel = START_VEL - round(player["score"]/14)
		if vel <= 1:
			vel = 1

		# get key presses
		keys = pygame.key.get_pressed()

		data = ""
		# MOVING IN GAME
		if keys[pygame.K_LEFT]:
			if player["x"] - vel - PLAYER_RADIUS - player["score"] >= 0:
				player["x"] = player["x"] - vel

		if keys[pygame.K_RIGHT]:
			if player["x"] + vel + PLAYER_RADIUS + player["score"] <= INNER_WIDTH:
				player["x"] = player["x"] + vel

		if keys[pygame.K_UP]:
			if player["y"] - vel - PLAYER_RADIUS - player["score"] >= 0:
				player["y"] = player["y"] - vel

		if keys[pygame.K_DOWN]:
			if player["y"] + vel + PLAYER_RADIUS + player["score"] <= INNER_HEIGHT:
				player["y"] = player["y"] + vel

		data = "move " + str(player["x"]) + " " + str(player["y"])



		# SEND DATA KE SERVER
		balls, players, game_time = server.send(data)

		# DRAW MESSAGE BOX
		# msg_count = len(msg_history)

		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				run = False

			if event.type == pygame.MOUSEBUTTONDOWN:
				if input_rect.collidepoint(event.pos):
					rect_status = 2
				else:
					rect_status = 1

			if event.type == pygame.KEYDOWN:
				if event.key == pygame.K_ESCAPE:
					run = False

				if rect_status != 1:
					if event.key == pygame.K_BACKSPACE:
						user_msg = user_msg[:-1]
						rect_status = 2

					elif len(user_msg) == 36:
						rect_status = 3

					elif event.key == pygame.K_RETURN:
						# if msg_count == 20:
						# 	msg_history = msg_history[1:]
						# 	msg_history.append(user_msg)
						# else:
						# 	msg_history.append(user_msg)
						data = "msg {}: {}".format(name, user_msg)
						msg_history = server.send(data)
						user_msg = ''

					else:
						user_msg += event.unicode

		# Redraw & Update frame
		redraw_window(players, balls, game_time, player["score"])

		data = "history"
		msg_history = server.send(data)

		pygame.draw.rect(window,color_passive,history_rect,2)
		history_rect.w = max(100,329)

		y = 0
		for msg in msg_history:
			history_surface = base_font.render(msg,True,(0,0,0))
			window.blit(history_surface,(INNER_WIDTH + 15, 30 + y * 30))
			y += 1

		if rect_status == 1:
			color = color_passive
		elif rect_status == 2:
			color = color_active
		else:
			color = color_warning

		pygame.draw.rect(window,color,input_rect,2)

		text_surface = base_font.render(user_msg,True,(0,0,0))
		window.blit(text_surface,(input_rect.x + 5, input_rect.y + 5))

		input_rect.w = max(329,text_surface.get_width() + 9)

		pygame.display.update()


	server.disconnect()
	pygame.quit()
	quit()

# get users name
while True:
 	name = input("Please enter your name: ")
 	if  0 < len(name) < 20:
 		break
 	else:
 		print("Error, this name is not allowed (must be between 1 and 19 characters [inclusive])")

# setup pygame window
os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (0,30)

# start game
main(name)
