# Poker probability calculator
Made in Python 3 for Texas Hold'em poker

Application input: Image of poker table

Application output: Probabilities of win/draw for each player

This repository contains GUI that:
* Can generate synthetic poker tables with random number of players with random cards
* Detects and identifies all poker cards on the table with a trained CNN included in this repository
* Analyses the state of the game; which player has which cards
* Computes probability of win/draw for each player with Monte-Carlo simulations
* Simulates next game state

<p align="center"> 
<img src="https://raw.githubusercontent.com/hrdlickajan/DP/master/img/vzor.PNG">
</p>

### Install
All used libraries are specified in file requirements.txt
```
pip install -r requirements.txt
```

### Usage
1. run poker.py
2. Button "Načti síť" - vybrat složku se sítí v tensorflow - "sit_final_sety", po úspěšném načtení se zaškrtne checkbox "síť načtena"
3. lze buď načíst reálný obrázek stolu pomocí tlačítka "Načti obrázek" (vzorové obrázky stolu jsou ve složce "obrazky")
4. nebo generovat náhodný syntetický obrázek tlačítkem "Generuj náhodný obrázek"
5. Tlačítko "Rozpoznej karty" identifikuje pokerové karty a přiřadí je hráčům
6. "Odkryj karty" vygeneruje místo otočených karet na stole náhodnou hrací kartu
7. "Spočti pravděpodobnosti" provede několik simulací pokerových her a vypíše pravděpodobnosti výhry/remízy pro každého hráče
