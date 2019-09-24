#!/usr/bin/env python3
# sample word game client source for ST2411, ST2512 assignment 2017
import sys
import socket
import random
import re
import signal
import time
from  wgEngine2017 import WGEngine, BColors
TIMEOUT = 10 # default 10 seconds timeout for keyboard input.
#PENALTY = 20
NON_USED = 2
SLOW_PENALTY = 5
REJECT_OR_TMOUT = 10
HALT_NOW = 20
WINNING_SCORE = 50
MAX_ROUND = 50
RESPONSE_LIMIT=40
SLOW_RESPONSE = 30
#
PORT_NO = 8899  # server port
def getnewsocket():
    return socket.socket(socket.AF_INET, socket.SOCK_STREAM)
def interrupted(signum, frame):
    # a signal triggered function,
    #it raises a ValueError once it is triggered.
    raise ValueError("interrupted")
    #print ("interrupted")

def my_input(prompt,tm=TIMEOUT,defval=None):
    signal.signal(signal.SIGALRM, interrupted)
    signal.alarm(int(tm))
    try:
        data = input(prompt).strip()
        signal.alarm(0)
        if data == '':
            data=defval
        return data
    except:
        # timeout
        return defval  
def get_word(prompt,tm=RESPONSE_LIMIT,defval="\n"):
    # get_word is almost identical to my_input, except, it returns
    # a None upon timeout.
    signal.signal(signal.SIGALRM, interrupted)
    signal.alarm(int(tm))
    try:
        data = input(prompt).strip()
        signal.alarm(0)
        if data == '':  #The user only press the Enter Key
            return defval
        return data
    except:
        # timeout
        return None  
def playgame(serverAddress):
    print('''
    +-----------------------------------+
    | Welcome to the ST2411 Playground! |
    +-----------------------------------+
    ''')
    cmd=""
    while cmd != 's':
        cmd = my_input("Type [s]tart to start, [h]elp for help, [o]verview for game objective or [q]uit =>",defval="q")
        if cmd in ['h','o']:
            if cmd == 'o':
                cmd='l' # to show overview of solo game
            WGEngine.showmenu(cmd)
        elif cmd == 'q':
            return

    bcolors = BColors()
    #define a SIGALRM event handler
    try:
        clientsocket = getnewsocket()
        clientsocket.connect(serverAddress) 
        clientsocket.settimeout(RESPONSE_LIMIT + 2.0)
        player = my_input("Player Name =>",tm=TIMEOUT,defval="Anonymous 1")
        print("Player is ",player)
    except Exception as ee:
        print("Sorry cannot connect to server.")
        print(ee)
        sys.exit(-1)
    if player != None: # player should be at least 'anonymous 1'
        try:
            clientsocket.sendall(player.encode())
            #print("send ok")
            while True:
                # starting of a new round, always waiting a message
                # from the Server
                rawbuf = clientsocket.recv(2048)
                if len(rawbuf)>0:
                    buf=rawbuf.decode()
                else:
                    print("big problem")
                    break
                if buf[-1] == '*':
                    # This indicate the end of the game.
                    print(buf[:-1])
                    break
                else:
                    print(buf)

                newword = get_word("{0:}'s turn =>".format(player),tm=RESPONSE_LIMIT)
                if newword == None:
                    print("{0}\nsorry, you are too slow.{1}".format(bcolors.RED, bcolors.ENDC))
                    # The server side should detect the same problem.
                    # just loop again and wait for the server's message.
                    continue
                #There is something to send to the server.
                clientsocket.sendall(newword.encode())
        except socket.error:
            print("Sorry. network error.")
             
    clientsocket.close()
#main function starts here
def main():
        # ask for server address before the starting the game.
    choice=""
    while not choice in ['l','c','q']:
        choice = my_input("Server type ? [l]an , [c]loud or [e]xit =>",defval="e")
        if choice == 'l':
            playgame(('localhost', PORT_NO))
        elif choice == 'c':
            playgame(('dmit2.bulletplus.com',80))      
        elif choice == 'e':
            return

# program starts here
main()
print("\nSee you again Soon.")
