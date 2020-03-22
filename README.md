# Diplomová práce
Zpracováno v Python 3. Repositář obsahuje GUI pro detekci pokerových karet a počítání pravděpodobností hráčů na výhru. 
Lze vygenerovat obrázek ze syntetických dat, která jsou tvořena ze 3 setů.

<p align="center"> 
<img src="https://raw.githubusercontent.com/hrdlickajan/DP/blob/master/img/vzor.PNG">
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
6. "Spočti pravděpodobnosti" provede několik simulací pokerových her a vypíše pravděpodobnosti výhry/remízy pro každého hráče
