
import sys
import string
from player import Player
#This is script is meant for spwaning a chosen number of instances, does not act like a master node

if __name__ == '__main__':

    a = sys.argv
    
    letters = string.ascii_uppercase
    
    if len(a) == 1:
        print(''' 
Usage: python mainTestingScript.py <num of players> <starting port>
This will create <num of players> players, all on localhost, with their port incrementing
from the starting port.
              ''')
    if len(a) == 3:
        players = []
        num = int(a[1])
        startingPort = int(a[2])
        for i in range(num):
            
            val = i
            name = ""
            
            while val >=0:
                name += letters[val%26]
                val //= 26
                if val == 0:
                    break
            if i != num - 1:
                p = Player(name, 'localhost', startingPort + i, "localhost", startingPort + i + 1)
            else:
                p = Player(name, 'localhost', startingPort + i, "localhost", startingPort)
            players.append(p)
        
        for p in players:
            p.start()
        
        for p in players:
            p.join()
    print("exiting main script.")