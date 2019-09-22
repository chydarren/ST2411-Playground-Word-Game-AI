#!/usr/bin/env python3 
''' 
Author: chydarren

File Name: soloServer.py
All Files: soloServer.py, wgEngine.py
To execute, type "python3 soloServer.py"
'''

# references
''' 
Certain algorithms have been adapted/modified from the following sites/files: 
1. Handle Multiple Clients - http://ilab.cs.byu.edu/python/select/echoserver.html
2. List Index Out of Range - https://stackoverflow.com/questions/5653533/indexerror-list-assignment-index-out-of-range
3. Cutting and Slicing Strings - http://pythoncentral.io/cutting-and-slicing-strings-in-python/
4. Print or Join Specific Elements - https://stackoverflow.com/questions/22275904/how-to-print-or-join-specific-elements-of-a-list-python
5. Python Lecture 7 - Multi-thread Server 
6. Python Solo Word Game - wordgame2017_solo.py 
'''

# learning resources
''' 
Learning resources and related notes were read from the following sites:
1. Sockets - https://docs.python.org/2/library/socket.html
2. Wait for I/O - https://pymotw.com/2/select/
3. Kill Process - https://stackoverflow.com/questions/11583562/how-to-kill-a-process-running-on-particular-port-in-linux
4. Queue - https://docs.python.org/2/library/queue.html
5. Multiple Variables with Same Value - https://stackoverflow.com/questions/16348815/python-assigning-multiple-variables-to-same-value-list-behavior
'''

# import the modules 
import select
import signal 
import sys
import socket
import queue 
import time 
import threading
import random
from wgEngine2017 import * 

# definitions (scores) 
# Scores to be added or deducted.
SC_SLOW = 5
SC_REJT = 10
SC_HALT = PTY = 20
SC_WIN = 50

# definitions (misc)
# Miscalleneous variables.
TMOUT = 10
REP_SLW = 30
REP_LMT = 40
MAX_RND = 50

# definitions (colors)
# Colors. 
RED = BColors.RED
BLU = BColors.BLU
GRN = BColors.GRN
END = BColors.ENDC

# function: validate word and generate print statements 
# Validates the word and generates the penalty/success statements. 
'''
Input Parameter(s): Buf, Engine Class, MainDict Class, P/AI Output List, Player Number, Time Difference 
Return Value: True / False 
'''
def generator(buf, engine, maindict, output, pnum, tmdiff):
    
    # response time 
    output[2] = str("\n{0}response time : {1} s{2}\n".format(GRN,'%.2f' % tmdiff,END))
    
    # case a - (✗) fail to respond 
    if buf == None:
        engine.players[pnum]["score"] -= SC_REJT
        output[0] = str("\n{0}Input time out. {1} points penalty. {2}".format(RED,SC_REJT,END))
        return True
    # case b - (✗) quit
    if buf == 'q':
        engine.players[pnum]["score"] -= SC_HALT
        output[0] = str("\n{0}Termination Request Accepted. {1} points penalty. {2}".format(RED,SC_HALT,END))
        return False  
    # case c, d, e, f, g, h - (✗) input word is not valid 
    isok, mesg = engine.isValid(buf,maindict)
    if (not isok):
        engine.players[pnum]["score"] -= SC_REJT
        output[0] = str("{0}{1} {2} points penalty. {3}".format(RED,mesg,SC_REJT,END)) 
        return True
    # case i - (✓) word accepted
    # (✓) +2: challenge letter(s)
    # (✗) -1: unused letter(s)
    c_score,score_str = engine.compute_score(buf)
    output[0] = str("\n" + score_str + "\n")
    
    # (✗) -5: slow response 
    if pnum == 0 and tmdiff > REP_SLW:
        c_score -= SC_SLOW 
        output[1] = str("{0}Response too slow. {1} points penalty.{2}".format(RED, SC_SLOW, END))
        
    # score tabulation
    engine.players[pnum]["score"] += c_score 

    # update words 
    engine.add_used_word(buf)
    engine.curword = buf
    return True  

# function: ai turn 
# AI will play on its own and validate its input accordingly. 
'''
Input Parameter(s): Engine Class, MainDict Class, AI Output List, Player Number, Mutation Finder
Return Value: True / False 
'''
def aiTurn(engine, maindict, aout, pnum, ai):
    
    # retrieve input word / quit 
    if engine.players[1]["score"] - engine.players[0]["score"] < PTY:
        buf = ai.findMutation(engine.curword,engine.mydict)
    else:
        buf = 'q'
        
    # validate word and generate print statements 
    aout[1] = str("\n{0} => {1}\n".format(engine.players[pnum]["name"], buf))
    if generator(buf, engine, maindict, aout, pnum, 0): 
        return True 
    else:
        return False 

# function: user turn
# User will be played by the client and validate its input accordingly.
'''
Input Parameter(s): Engine Class, MainDict Class, Player Output List, Buf, Player Number 
Return Value: True / False 
'''
def userTurn(engine, maindict, pout, buf, tmdiff, pnum=0):

    # validate word and generate print statements 
    if generator(buf, engine, maindict, pout, pnum, tmdiff): 
        return True 
    else:
        return False 
      
# function: round statement
# Generate the statements for each round. 
'''
Input Parameter(s): Round Output List, Players, Round Number, Current Word
Return Value: - 
'''
def roundstatement(rnd, players, round, curword):
  
    # round statement 
    rnd[0] = str("\n\nAt Round {0} \n".format(str(round)))
    for i in range(2):
        rnd[i+1] = str("{0} scores: {1}   ".format(players[i]["name"],players[i]["score"]))
    rnd[3] = str("\nCurrent word: {0}{1}{2}\n".format(BLU,curword,END))

# function: manage game (aka handler)
# Manages the entire game 
'''
Input Parameter(s): Connection, Queue, Client Address, MainDict Class, Engine Class
Return Value: True 
1. At the beginning of the game instance, get player name first.
2. After getting player name, ctr+=1 to enter the proper rounds.
3. Print statements will be generated at each turn and compiled together to form single con.sendall("...").
4. Each quit of game instance will put "q" into the common queue.
5. If common queue detects that all clients have quitted, the server will halt itself.
'''
def managegame(con,q,client_addr,maindict,engine):
    
    # important variables 
    con.settimeout(REP_LMT)
    ai = MutationFinder(maindict)
    ctr = idle = 0 
    
    # player variables 
    prnd = [""] * 4    # each line in the round statement 
    pout = [""] * 3    # error / score statement: pout[0] , response time: pout[2], response slow: pout[1]
    
    # ai variables 
    arnd = [""] * 4    
    aout = [""] * 3    # error / score statement: aout[0] , response time: aout[2], input word: aout[1] (ai) 
    
    # retrieve current word 
    engine.curword = random.choice(list(maindict.mDict.keys()))
    engine.add_used_word(engine.curword)
    
    while True:

        # retrieve current turn
        pnum = (engine.round+1) % 2
        
        # player's turn 
        if pnum == 0: 
            if ctr != 0:
                # generate round statement 
                roundstatement(prnd, engine.players, engine.round, engine.curword)
                # send all output (player's round statement and previous ai turn (if any))
                con.sendall((pout[2] + "".join(pout[0:2]) + "".join(arnd) + "".join(aout[1:3]) + aout[0] + "".join(prnd)).encode())
                # reinitialize the player output, ai output and ai round statements 
                pout = [""] * 3
                aout = [""] * 3
                arnd = [""] * 4
            # retrieve player input 
            try:
                starttm = time.time() 
                buf = con.recv(255).decode() 
                tmdiff = time.time()-starttm
                
                # check for attempt to quit / idle  
                if len(buf) > 0:
                    idle = 0
                    if buf == "q":
                        q.put(buf)
                else:
                    q.put("q")
                    return 

                # perform tasks 
                if ctr == 0: 
                    # retrieve player names
                    engine.players[0]["name"] = buf 
                    engine.players[1]["name"] = 'betagone' 
                else: 
                    if not userTurn(engine,maindict,pout,buf,tmdiff,pnum):
                        break     
                        
            # retrieve fail; exception occured 
            except Exception as inst:
                if str(inst) == "timed out":
                    idle += 1 
                    buf = None 
                    if not userTurn(engine,maindict,pout,buf,REP_LMT,pnum):
                        break 
                if flag or idle > 4 or (str(inst) != "timed out"):  
                    q.put("q")
                    break
        # ai's turn 
        else:
            # generate round statement 
            roundstatement(arnd, engine.players, engine.round, engine.curword)
            # ai turn 
            if not aiTurn(engine,maindict,aout,pnum,ai):
                break   

        # round tabulation 
        if(ctr != 0):
            if engine.round >= MAX_RND or (engine.round%2 and (engine.players[0]["score"] >= SC_WIN or engine.players[1]["score"] >= SC_WIN)):                
                break 
            engine.round += 1
        else:
            ctr += 1 

    # final statement 
    final = str("{0}{1}{2}\n".format(BLU,engine.get_final_scores(),END))
    if engine.isDrawn():
        con.sendall((pout[2] + "".join(pout[0:2]) + "".join(arnd) + "".join(aout[1:3]) + aout[0] + final + ("{0}Wow, what a close fight, both of you are winners! {1}*".format(BLU,END))).encode())
    elif engine.isPlayerWon():
        con.sendall((pout[2] + "".join(pout[0:2]) + "".join(arnd) + "".join(aout[1:3]) + aout[0] + final + str("{0}Congratulation to {1}, you are the champion! {2}*".format(BLU,engine.players[0]["name"],END))).encode())
    else:
        con.sendall((pout[2] + "".join(pout[0:2]) + "".join(arnd) + "".join(aout[1:3]) + aout[0] + final + str("{0}{1}, you have put up a good fight, try harder next time. {2}*".format(BLU,engine.players[0]["name"],END))).encode())
    con.close()
    q.put("q")
    return

# function: set up multithread server
# This function is required to provide the multithread features.
'''
Input Parameter(s): -
Return Value: - 
'''
def multithread():
    
    # establish server socket 
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('localhost', 8899))
    server.listen(5) 
    print("Server starts listening ...")

    # establish the connection
    commonq = queue.Queue(20)
    clients = 0
    global flag  
    flag = False
    server.settimeout(TMOUT) 
    while True:
        try:
            # accept the connection 
            if not flag:
                try:
                    con, client_addr = server.accept() 
                    clients += 1
                    print('No. of active clients increased to {}'.format(clients))
                    t = threading.Thread(target=managegame, args=(con,commonq,client_addr,MainDict(),WGEngine()))
                    t.start()
                except Exception as inst:
                    if str(inst) != "timed out": 
                        break
                    print("Accept timeout. Time to check the common queue")
            # no more active clients 
            elif clients == 0:
                break 
            # check the queue 
            if not commonq.empty():
                data = commonq.get()
                clients -= 1
                print('No. of active clients reduced to {}'.format(clients))
                if data == 'q' and clients == 0:
                    flag = True
        except KeyboardInterrupt:
            flag = True

    # close server socket
    server.close()                
    print("Server has halted.")

# main function
def main():
    multithread()

# start
if __name__ == '__main__':
    main()
