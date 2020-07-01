# Poker probability calculator
Works for Hold'em version
Input: image of poker table
Output: Probabilities of win/draw for each player
This repository contains GUI that:
* Can generate synthetic poker tables with random number of players
* Detects and identifies all poker cards on the table with a trained CNN
* Analyses the state of the game; which player has which cards
* Computes probability of win/draw for each player with Monte-Carlo simulations
* Simulates next game state

<p align="center"> 
<img src="https://raw.githubusercontent.com/hrdlickajan/DP/master/img/vzor.PNG">
</p>

### Install
Soubor s použitými moduly je v tomto repozitáři

```
pip install -r requirements.txt
```

### Použití
Stáhnout a rozbalit/klonovat tento repozitář
1. spustit poker.py
2. tlačítko "Načti síť" - vybrat složku se sítí v tensorflow - "sit_final_sety", po úspěšném načtení se zaškrtne checkbox "síť načtena"
3. lze buď načíst reálný obrázek stolu pomocí tlačítka "Načti obrázek" (vzorové obrázky stolu jsou ve složce "obrazky")
4. nebo generovat náhodný syntetický obrázek tlačítkem "Generuj náhodný obrázek"
5. Tlačítko "Rozpoznej karty" identifikuje pokerové karty a přiřadí je hráčům
6. "Odkryj karty" vygeneruje místo otočených karet na stole náhodnou hrací kartu
7. "Spočti pravděpodobnosti" provede několik simulací pokerových her a vypíše pravděpodobnosti výhry/remízy pro každého hráče
