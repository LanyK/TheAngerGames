# The Anger Games

*Exploring the Concept of Anger as a Game Element* <br>
The paper to this project is included in this repository at https://github.com/LanyK/TheAngerGames/blob/master/The_Anger_Games_Paper.pdf

## Group Members

- A. Perzl
- M. Zierl
- M. Bachmaier
- Y. Kaiser

## Repository Overview

- **bombangerman** holds the main project of devising and implementing a multiplayer game that tracks and uses the players' emotional state. This is the **main** part of this project
- **face-emotion-recognition** holds software created and used to train a neural facial emotion recognition model
- **popup-shutdown** holds a small web game that was an early test of frustration-inducing gameplay
- **simple-server** holds a test server devised to send dummy and real emotion data
- **e4-ios** holds an iOS app that is used to connect to Empatica E4 wristbands and send the data to the server

## Bombangerman

### About

*Bombangerman* is a [Bomberman](https://en.wikipedia.org/wiki/Bomberman) clone that incorporates emotion detection into the main gameplay loop. Players are tracked via facial emotion recognition and them becoming angry triggers increased difficulty for the angry player. Additionally, the program can track data from an Epatica E4 wristband and record game sessions, including data gathered this way. The programs are created for **Python 3.6**.

### How To Run

To run the full stack, adhere to the following steps, installing python dependencies as prompted.

On the Server Machine (can be a Client Machine simoultanously):
- start ./bombangerman/server/Server.py
- start ./bombangerman/server/AngerBroadcaster.py

On both Client Machines:
- start ./bombangerman/client/Client.py and wait in the main menu
- start ./bombangerman/client/Face_Recognition_Client.py

Both Clients:
- start the game via entering the server IP

Including Empatica E4 wristband:
- run the ./e4-ios App on an device with iOS 12 and follow the readme instructions in ./e4-ios/
- after the app has started insert the IP adress of the server

### Recordings

To enable recordings, run the server with the **-s** flag set.

To display a recording, run ./bombangerman/client/GameReplay.py <TimeStamp>, where <TimeStamp> is the folder name of one of the replay folders in ./bombangerman/replays/
  
### Controls

The game controls are:
- **I** - move up
- **J** - move left
- **K** - move down
- **L** - move right
- **Space** - place a bomb
- **U** - Taunt
- **O** - Slime the enemy

## Popup-Shutdown

Run by starting ./popup-shutdown/index.html in a web browser
