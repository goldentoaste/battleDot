from multiprocessing.connection import Client, Connection
from multiprocessing import Process
from multiprocessing.connection import Listener
from enum import Enum
from random import Random

from threading import Thread
from time import sleep
from datetime import datetime

from typing import List, Tuple, Dict

import sys 
rng = Random()


def getRandPos():
    return (rng.randint(1, 10), rng.randint(1, 10))


class MsgTypes(Enum):
    BASE = 0
    FIRE = 1
    HIT = 2
    DSTRY = 3  # destroyed
    OVER = 4
    ROLL = 5
    RETARGET = 6
    START = 7


class Msg:
    def __init__(self, sender: Tuple[str, int], path: List[Tuple[str, int]] = None) -> None:

        self.msgType = MsgTypes.BASE
        self.sender = sender
        self.path = path if path else []  # path is optionally empty list


class FireMsg(Msg):
    def __init__(self, sender: Tuple[str, int], target: Tuple[int, int]) -> None:
        super().__init__(sender)
        self.msgType = MsgTypes.FIRE
        self.target = target


class HitConfirmMsg(Msg):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.msgType = MsgTypes.HIT


class DestroyedMsg(Msg):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.msgType = MsgTypes.DSTRY


class GameOverMsg(Msg):
    # game over occurs when there is only 1 player remaining
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.msgType = MsgTypes.OVER


class RollCallMsg(Msg):
    # game over occurs when there is only 1 player remaining
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.msgType = MsgTypes.ROLL


class GameStartMsg(Msg):
    # game over occurs when there is only 1 player remaining
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.msgType = MsgTypes.START


class RetargetMsg(Msg):
    # game over occurs when there is only 1 player remaining
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.msgType = MsgTypes.RETARGET


class Player(Process):
    def __init__(
        self,
        name: str,
        ip: str,
        port: int,
        otherIp: str,
        otherPort: int,
        startOnRun=True,
        doRollCall=False,
        insertAddress=None,
    ) -> None:
        super().__init__()
        self.name = name
        self.address = (ip, port)
        self.opponent = (otherIp, otherPort)
        self.realNeighbor = (otherIp, otherPort)
        self.receiver = Listener(self.address)

        self.threads: List[Thread] = []
        self.outBoundConnections: Dict[Tuple[str, int], Client] = {}
        self.clientTaskList = []
        
        

        # lots of state flags
        self.insertAddress = insertAddress
        self.doRollCall = doRollCall
        self.gameStarted = startOnRun
        self.gameEnded = False
        self.isAlive = True
        self.canFire = True

        self.dot: Tuple[int, int] = getRandPos()
        
    def log(self, info:str):
        self.logFile.write(f"{self.name}, {datetime.now().strftime('%H:%M:%S')}: {info}\n")

    def clientHandling(self):
        while not self.gameEnded:
            if self.clientTaskList:
                addr, callback, args = self.clientTaskList.pop(0)
                if addr not in self.outBoundConnections:
                    self.outBoundConnections[addr] = Client(addr)
                callback(*args, self.outBoundConnections[addr])
            sleep(0.001)

    def getClient(self, addr: Tuple[str, int], callback, *args) -> Client:
        if addr in self.outBoundConnections:
            return callback(*args, self.outBoundConnections[addr])

        self.clientTaskList.append((addr, callback, args))

    def run(self) -> None:
        
        print(f"{self.name} starting")
        self.logFile = open(f"{self.name}.log", mode='w')
        self.log(f"starting with addr: {self.address}, neighbor is : {self.opponent}, dot is at {self.dot}.")
        
        self.clientMakingThread = Thread(target=self.clientHandling)
        self.clientMakingThread.start()

        self.firingThread = Thread(target=self.fireLoop)
        self.firingThread.start()

        if self.doRollCall:
            print(f"{self.name} doing roll call")
            self.log(f"Starting roll call")
            self.getClient(self.opponent, lambda client: client.send(RollCallMsg((self.name, self.address))))
        elif self.insertAddress:
            
            print(f"{self.name} inserting after {self.insertAddress}")
            self.getClient(self.insertAddress, lambda client: client.send(RetargetMsg(sender = (self.name, self.address))))

        while not self.gameEnded:
            con = self.receiver.accept()
            t = Thread(target=self.handleConnection, args=[con])
            t.start()

        print(f"{self.name} finished main event loop, starting clean up")
        self.log("cleaning up")
        
        # clean ups
        
        
        self.receiver.close()
        for client in self.outBoundConnections.values():
            client.close()
        for t in self.threads:
            t.join()
        self.clientMakingThread.join()
        self.firingThread.join()
        print(f"{self.name} finished")
        
        
        self.log("clean up done.")
        self.logFile.close()

    def handleFire(self, msg: Msg, client: Client):
        assert type(msg) == FireMsg, f"{msg.msgType}, addr: {msg}"

        if self.gameEnded:
            return

        if msg.sender[1] == self.address:
            print(f"\n\n!!{self.name}, {self.address} has won!!\n\n")
            self.log("\n\n!!!!Victory!!!!\n\n")
            self.getClient(
                self.realNeighbor, lambda client: client.send(GameOverMsg((self.name, self.address)))
            )
            self.endGame()
            return

        if not self.isAlive:
            msg.path.append((self.name, self.address))
            print(f"received fire from {msg.sender[0]}, forwarding to {self.opponent}")
            self.log(f"received fire from {msg.sender[0]}, forwarding to {self.opponent}")
            self.getClient(
                self.opponent, lambda msg1, client1: client1.send(msg1), msg
            )  # forward the fire msg
            return

        if msg.target == self.dot:
            # self hit by the sender of fire msg
            print(f"{self.name} am detroyed by {msg.sender}")
            self.log(f"I have been destroyed by {msg.sender}")
            self.isAlive = False
            client.send(DestroyedMsg(sender=(self.name, self.address)))
        else:
            self.log(f"Shot from {msg.sender[0]}, target: {msg.target}, missed.")
            client.send(HitConfirmMsg(sender=(self.name, self.address)))

    def handleConnection(self, conn: Connection):

        while not self.gameEnded:

            try:
                msg = conn.recv()
            except EOFError:
                # this only occurs when multiple connections on the same addr is made
                # which only occurs during the hack in self.endGame, all other cases shouldnt taken care of.
                continue

            assert isinstance(msg, Msg)  # the data coming must be a Message now
            if self.gameEnded:
                return

            print(f"msg from {msg.sender} received by {self.address}, type: {type(msg)}")
            if msg.msgType == MsgTypes.FIRE:
                self.log(f"received Fire msg from {msg.sender[0]}")
                self.getClient(
                    msg.sender[1], lambda msg, client: self.handleFire(msg, client), msg
                )  # the the client and msg to handleFire
            elif msg.msgType == MsgTypes.HIT:
                # received a hit confirmed from a previous shot fired
                self.log(f"hit confirmed from {msg.sender[0]} "+f'changing opponent to {msg.sender[1]}, was {self.opponent}')
                self.canFire = True
                self.opponent = msg.sender[1]
            elif msg.msgType == MsgTypes.DSTRY:
                # target destroyed! but no need to update opponent yet.
                self.log(f"destroyed {msg.sender[0]}")
                self.canFire = True
            elif msg.msgType == MsgTypes.OVER:
                # set the state of self to game ended
                
                if (
                    msg.sender[1] != self.address
                ):  # stop sending if the game over msg has looped with every player, also edge case with one player
                    print(f"{self.name} received game over, shutting down.")
                    self.log(f"Game over received, shutting down.")
                    msg.path.append((self.name, self.address))
                    self.getClient(
                        self.realNeighbor, lambda msg, client: (client.send(msg), self.endGame()), msg
                    )

            elif msg.msgType == MsgTypes.ROLL:
                if msg.sender[1] != self.address:
                    self.log(f"roll call received, origin: {msg.sender[0]}, forwarding.")
                    # the roll call has no finished yet, just append self and move on
                    msg.path.append((self.name, self.address))
                    self.getClient(self.opponent, lambda msg, client: client.send(msg), msg)
                else:
                    # the roll call has went all the way around
                    print("roll call has finished! Printing all called player.")
                    self.log("roll call has finished! Printing all called player.")
                    for addr in msg.path:
                        print(addr)
                        self.log(addr)
                    print((self.name, self.address))
                    self.log((self.name, self.address))

                    print("sending each player the start message.")
                    self.log("sending each player the start message.")

                    for addr in msg.path:
                        self.getClient(
                            addr[1], lambda client: client.send(GameStartMsg((self.name, self.address)))
                        )
                    self.gameStarted = True  # start own game as well

            elif msg.msgType == MsgTypes.START:
                self.log("start msg received, starting.")
                self.gameStarted = True
            
            elif msg.msgType == MsgTypes.RETARGET:
                self.log(f"retarget msg received, neighbor is now {msg.sender[0]}, was {self.realNeighbor}")
                if self.isAlive:
                    self.opponent = msg.sender[1] 
                self.realNeighbor = msg.sender[1] # real neighbor needs to be adjusted to keep the linked list connected.
                self.getClient(msg.sender[1], lambda client: client.send(GameStartMsg((self.name, self.address))))

    def endGame(self):
        self.gameEnded = True
        try:
            # what an awful way to stop
            c = Client(self.address)
        except Exception as e:
            pass

    def handleSendingFire(self, sender):
        pos = getRandPos()
        print(f"{self.name} sending fire msg to {self.opponent}, target : {pos}")
        self.log(f"sending fire msg to {self.opponent}")
        sender.send(FireMsg(sender=(self.name, self.address), target=pos))

    def fireLoop(self):
        if not self.gameStarted:
            print(f"firing thread of {self.name} is waiting for game to start.")
            self.log("waiting for game/roll call to start")
            while not self.gameStarted:
                sleep(0.1)

        while not self.gameEnded and self.gameStarted and self.isAlive:
            if self.canFire:
                self.canFire = False
                self.getClient(self.opponent, self.handleSendingFire)
            sleep(0.25)
        print(f"{self.name} has left fireloop")
        self.log(f"{self.name} has left fireloop")


if __name__ == "__main__":
    

    a = sys.argv
    if len(a) == 6:
        p = Player(a[1], a[2], int(a[3]), a[4], int(a[5]), False )
    elif len(a) == 7:
        p = Player(a[1], a[2], int(a[3]), a[4], int(a[5]), False, a[6].lower() == "true" )
    elif len(a) == 9:
        p = Player(a[1], a[2],int(a[3]), a[4], int(a[5]), False, a[6].lower() == "true",(a[7], int(a[8])) )
    else:
        raise ValueError(f"Wrong number of params, expected, 6, 7, or 9, got {len(a)}")
    
    p.run()
    
