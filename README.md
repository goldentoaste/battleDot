

# Battle Dot
### April 1st, 2022
---

## Lauch:
1. Testing on local machine: 
    * `python mainTestingScript.py <number of players> <starting port>`
    * this wills start `<number of players>` processes, all on localhost, witch incrementing port number, starting from `<starting port>`
    * this script is only for lauching the processes, and does not function like a master node.
    * for exmaple `python mainTestingScript.py 4 6000` starts a game with 4 players, port 6000, 6001, 6002, 6003 will be used.
2. Setting manually, or testing on remote machines:
    * `python player.py <name> <player ip> <player port> <opponent ip> <opponent port> [final player (true/false)] [<insertion ip> <insertion port>]`
        * players delcared this way will wait until 'final player' is declared
        * final player is optional, if this is set to true, then this player will send a 'start game' message to every other player and the game starts.
        * insertion ip and insertion ports are also optional, and should be used after the game starts. If these 2 params are present, this player will be inserted after `insertion ip, port`, and play against `opponent ip, oppent port`

    * example: 
    ```
    python player.py A localhost 6000 localhost 6001
    python player.py A localhost 6001 localhost 6000 true
    ```
    * This will start a game with 2 players
    * The ip and ports delcared could for a remote machine, as long as a tcp connection could be made. I was not able to test this due to limited time, but no part of the code assumes local connecton, so the code should work.

## Interpreting:
All sent and received messages are logged both in file (`playerName.log`) and printed to console. Each player writes their own log file. Players destroyed are logged. When there is only 1 player after, that player is delcared the winner.

## Some explaination of the code
* Each process is a python multiprocess.Process, unless they are spawned manually, since they are invidual processes already.
* Each process spawns a number of threads in order to process messages in each socket connection to other players. 
* Comnication between players are only peer to peer, via the following messages:
    * Fire: The player picks a random postion and fires/send this message to opponent. The player must wait for a 'Hit confirmed' in order to fire again.
    * Hit confirmed, is sent as a response to Fire. This message means that fire msg is received, but didnt hit the target. When the player who shot the projectile received the hit confirmed, it changes to opponent to the sender of the message.
        * If the player who received a Fire is dead, the message is forwarded to the next player, until a alive one is found. Then that alive player sends a hit confirmed to the oringinal player who fired.

    * Destroyed: is sent back as a response to Fire, marks the player dead. When a player receives a destroyed message, only resets the firing lock, and print a message. 

    * Game Over: Game over is declared when a single player's Fire message has been passed through every other player, and made it back, meaning every other player is dead. The winner then sends a game over message to its neighbor, and each neighbor passes passes to the next one. Each player who receives this message shuts down and exits.

    * Roll call, this is sent by a single player at the beginning, this message is then passed along until it made it back to the original player, who will then send a Start Game to every player visited.

    * Start Game: just indicates the game has started when received.

    * Retarget: This message is received when a player is to be inserted after the current one. Will change the current player  opponent and neighbor.

## Not implemented  / problems
* Removing player upon a player being terminated by external signal is not implemented. I think this should be via python's signal library, registering each process to listen to interupt or termination singals, then clean up/ link neighbors when the signals are received. But I didn't have enough time to get this work.

* Problems: It's possible that there is some race conditions / deck locks / other async problems I didn't get to fix. Namely the one I am aware of is that if 2 players(or more) sends Fire message and kills each other, there will be no players left to declare victory, and every process remains hanging. But this is very unlikely for non trivial number of players or board size. 

    
    