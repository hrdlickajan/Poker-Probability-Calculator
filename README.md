# Poker probability calculator
Made in Python 3 for Texas Hold'em poker

Application input: Image of poker table <br />
Application output: Probabilities of win/draw for each player

<p align="center">
<img src="https://raw.githubusercontent.com/hrdlickajan/DP/master/img/vzor.PNG">
</p>

This repository contains GUI that:
* Detects and identifies all poker cards on the table with a trained CNN included in this repository
* Analyses the state of the game; which player has which cards
* Computes probability of win/draw for each player with Monte-Carlo simulations
* Simulates the next game state
* Can generate digital images of poker tables with random number of players with random cards


### Install
All used libraries are specified in file requirements.txt
```
pip install -r requirements.txt
```

### Usage
1. run poker.py
2. Button "Load net" - choose folder CNN-cards to load neural network to classify cards
3. Button "Load image" - loads any image and displays it in GUI, some sample images with poker tables are in the folder "sample_images"
4. Button "Generate random image" - generates a synthetic poker image with random cards and random player count
5. Button "Identify" - identify all cards and assign them to players
6. Button "Next step" - simulates the next game state and shows it in GUI
7. Button "Compute probabilities" - computes probabilities of win and draw for every player and displays it in the table from highest to lowest

example order(s): 1-2-3(or 4)-5-6(or 7)

todo: rewrite code in english
