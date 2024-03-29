'''
GUI pro identifikaci pokerovych karet a spocitani pravdepodobnosti vyher a
remiz. Testovany obrazek lze bud generovat ze skriptu generator_stul.py nebo
ho lze nacist z realnych fotek
pokud byl tento skript naklonovan z githubu, realny fotky stolu jsou ve slozce
"obrazky".
Mozne pouzit:
1. Nacti neuronovou sit - sit_final sety je moje stavajici sit
2. Generuj/nacti/nech stavajici obrazek
3. Rozpoznej karty
4. Spocitej pravdepodobnosti - muze nejakou dobu trvat kvuli provadenym
simulacim
'''
import scipy.ndimage as ndimage
from PIL import Image
from skimage import img_as_ubyte
import cv2
import skimage.measure
from skimage.filters import threshold_otsu
from tensorflow.keras.models import Sequential
import pickle
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog
import qdarkstyle
import os
import random
import tensorflow as tf
import numpy as np
import itertools
import generator_karta
import sys

barvy_dict = {"S": "♠", "C": "♣", "H": "♥", "D": "♦"}  # mapovani barev
hodnoty = list(range(2, 15))  # ciselne hodnoty karet eso - 14, kral - 13...
hodnoty_str = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K',
               'A']
barvy = ["C", "S", "H", "D"]  # anglicke nazvy barev
kombinace = set()  # vsechny kombinace karet - celkem 52
for barva in barvy:
    for hodnota in hodnoty:
        kombinace.add(str(hodnota) + barva)
dostupne_karty = kombinace.copy()
# temito barvami budou konturovany karty + hraci maji tyto barvy v tabulce gui
barvy_hracu = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 255, 255),
               (255, 0, 255), (255, 255, 0)]
barva_stul = (125, 125, 125)  # barva kontur community karet
font = QtGui.QFont("Times", 10, QtGui.QFont.Bold)
karty_na_stole = []


def generujNahodnouKartu(set, rotace, vyska=528, sirka=378):
    global dostupne_karty  # pole se vsemi kartami, ktere se na stole nachazi
    barva = random.choice(barvy)
    hodnota = str(random.choice(hodnoty))
    nazev = hodnota + barva
    if nazev in dostupne_karty:
        dostupne_karty.remove(nazev)
        return (generator_karta.vytvorKartu(set, rotace, hodnota, barva,
                                            vyska, sirka), hodnota, barva)
    else:
        return (None, None, None)


class Stul:
    def __init__(self, karty_set, x=4000, y=3000, cesta="stul_temp.png",
                 stav_hry=0):
        self.cesta = cesta
        self.x = x
        self.karty_set = karty_set
        self.y = y
        self.img = Image.new('RGB', (x, y))
        self.flop_karty = []
        if stav_hry == 0:
            self.pocet_odkrytych_karet = 0
        elif stav_hry == 1:
            self.pocet_odkrytych_karet = 3
        elif stav_hry == 2:
            self.pocet_odkrytych_karet = 4
        else:
            self.pocet_odkrytych_karet = 5

    # vygeneruje karty na stole (community cards)
    def vygenerujFlopRiverTurn(self):
        souradnice_flop_pole = [[650, 1200], [1200, 1200], [1750, 1200],
                                [2300, 1200], [2850, 1200]]
        i = 0
        while len(self.flop_karty) < 5:
            # nahodna rotace karet
            self.flop_rotace = random.randrange(-15, 15, 1)
            souradnice_flop = souradnice_flop_pole[i]
            karta, _, _ = generujNahodnouKartu(self.karty_set,
                                               self.flop_rotace)
            if karta:
                if self.pocet_odkrytych_karet > 0:
                    self.pocet_odkrytych_karet -= 1
                else:
                    karta = generator_karta.vytvorPozadi(self.karty_set,
                                                         self.flop_rotace)

                self.flop_karty.append(karta)
                self.pridej(karta, souradnice_flop)
                i += 1

    # prida kartu do snimku stolu
    def pridej(self, img, souradnice):
        self.img.paste(img, souradnice)

    # ulozi obrazek stolu
    def uloz(self):
        self.img.save(self.cesta)


class Ruka:
    def __init__(self, karty):
        self.hodnoty = []
        self.barvy = []
        self.sila = 0
        for karta in karty:
            self.hodnoty.append(int(karta[:-1]))
            self.barvy.append(karta[-1])
        self.nejvyssiHodnota = max(self.hodnoty)  # nejvyssi karta na ruce
        self.nejnizsiHodnota = min(self.hodnoty)
        self.suma = sum(self.hodnoty)

# pokud je v setu barev 1 element, potom je vsech 5 barev stejnych
    def zkontrolujFlush(self):
        ruka = set(self.barvy)
        self.flush = len(ruka) == 1
        return self.flush

# po sobe jdouci hodnoty
    def zkontrolujStraight(self):
        ruka = set(self.hodnoty)
        pet_ruznych_hodnot = len(ruka) == len(self.hodnoty)
        po_sobe_jdouci = max(ruka) - min(ruka) == len(ruka) - 1
        self.straight = pet_ruznych_hodnot and po_sobe_jdouci
        return self.straight or ruka == set([2, 3, 4, 5, 14])  # 14 - eso

# tvori kombinace karet par? trojici? ctverici? fullhouse? 2 pary?
    def zkontrolujOpakovaniHodnoty(self):
        # kolikrat se hodnota vyskytuje v dane ruce
        suma = sum(self.hodnoty.count(r) for r in self.hodnoty)
        # priklad: kombinace hodnot karet 5 5 3 10 5
        # count pole pred sumou: [3, 3, 1, 1, 3], suma pole = 11 => trojice
        self.ctverice = suma == 17  # 4 + 4 + 4 + 4 + 1
        self.full_house = suma == 13  # 3 + 3 + 3 + 2 + 2
        self.trojice = suma == 11  # 3 + 3 + 3 + 1 + 1
        self.dva_pary = suma == 9  # 2 + 2 + 2 + 2 + 1
        self.par = suma == 7  # 2 + 2 + 1 + 1 + 1

    # sila ruky
    def vyhodnotSilu(self):
        if self.straight and self.flush and self.nejvyssiHodnota == 14:
            self.sila = 9  # royal flush
        elif self.straight and self.flush:
            self.sila = 9  # straight flush
        elif self.ctverice:
            self.sila = 8
        elif self.full_house:
            self.sila = 7
        elif self.flush:
            self.sila = 6
        elif self.straight:
            self.sila = 5
        elif self.trojice:
            self.sila = 4
        elif self.dva_pary:
            self.sila = 3
        elif self.par:
            self.sila = 2
        else:
            self.sila = 1  # high card


class Hrac:
    pocet_vyher = 0
    pocet_remiz = 0

    def __init__(self, id, karty_set):
        souradnice_pole = [[100, 300], [100, 2200], [2900, 300],
                           [2900, 2200], [1600, 300], [1600, 2200]]
        self.id = id
        self.karty = []
        self.karty_na_stole = []
        self.karty_set = karty_set
        self.souradnice = souradnice_pole[self.id]
        self.rotace = random.randrange(-15, 15, 1)

    # vytvori vsechny kombinace, ktere muzou nastat a vyhodnoti nejlepsi ruku
    def vyhodnotRuce(self):
        self.ruce = []  # vsechny kombinace ktere muzou nastat pro daneho hrace
        karty_num = []
        for karta in self.karty:
            karty_num.append(str(karta.hodnotaNum) + karta.barva)
        self.vsechny_karty = karty_num + self.karty_na_stole
        self.kombinace = itertools.combinations(self.vsechny_karty, 5)
        for karty in self.kombinace:
            ruka = Ruka(list(karty))
            ruka.zkontrolujFlush()
            ruka.zkontrolujStraight()
            ruka.zkontrolujOpakovaniHodnoty()
            ruka.vyhodnotSilu()
            self.ruce.append(ruka)

        # nejlepsi mozna kombinace karet
        self.nejlepsiRuka = sorted(self.ruce,
                                   key=lambda ruka: (ruka.sila,
                                                     ruka.nejvyssiHodnota,
                                                     ruka.suma)
                                   )[-1]

    # nacte karty pri generovani stolu
    def nactiKarty(self):
        while len(self.karty) < 2:
            karta, _, _ = generujNahodnouKartu(self.karty_set, self.rotace)
            if karta:
                self.karty.append(karta)

    # slouci karty do jednoho obrazku
    def slucKarty(self):
        self.img = Image.new('RGB', (self.karty[0].width +
                                     self.karty[1].width+40,
                                     self.karty[1].height))
        self.img.paste(self.karty[0], (0, 0))
        self.img.paste(self.karty[1], (self.karty[1].width+20, 0))


class Sit:
    # nacti sit pomoci cest k parametrum
    def __init__(self, model_cesta):
        self.sit = Sequential()
        try:
            self.sit = tf.keras.models.load_model(model_cesta)
        except OSError:
            self.sit_nactena = False
            return
        self.sit_nactena = True
        self.nacti_poradi()

    def nacti_poradi(self):  # nacti pickle soubor s poradim karet
        pickle_in = open("poradi_new.pickle", "rb")
        poradi = pickle.load(pickle_in)
        self.key_list = list(poradi.keys())
        self.val_list = list(poradi.values())

    # klasifikuj kartu
    def klasifikuj(self, karta):
        prediction = self.sit.predict(karta.karta_sit)
        vysledek = self.key_list[self.val_list.index(np.argmax(prediction))]
        karta.vysledek = vysledek
        if vysledek == "pozadi":
            karta.barva = "X"
            karta.hodnota = "X"
            karta.numerickaHodnota = 0
        else:
            karta.barva = vysledek[0]
            karta.hodnota = vysledek[1:]
            karta.numerickaHodnota()


class Snimek:
    # nacti snimek
    def __init__(self, snimek_cesta):
        self.color = cv2.imread(snimek_cesta)
        self.gray = cv2.imread(snimek_cesta, 0)
        self.kontury = cv2.imread(snimek_cesta)
        self.nazev_snimku = os.path.basename(os.path.splitext(snimek_cesta)[0])

    # segmentace pomoci otsu, labeling a mereni regionu
    def segmentace(self):
        prah = threshold_otsu(self.gray)
        self.segmentovany = self.gray > prah
        imgEr = ndimage.binary_closing(self.segmentovany,
                                       iterations=1).astype(np.int)
        # self.labely = skimage.measure.label(img_gray_thresh, background=0)
        self.labely = skimage.measure.label(imgEr, background=0)
        self.props = skimage.measure.regionprops(self.labely + 1)
        self.nastavPrah()

    # nastaveni prahu obsahu pro regionprops
    def nastavPrah(self):
        self.prah = 30000  # tohle jde asi udelat lip, ale funguje to

    # zkontroluje obsah labelu a pokud je obsah dostatecny, jedna se o kartu
    def ziskejKarty(self):
        karty = []
        for i in range(1, np.max(self.labely)+1):

            if not self.validaceRegionu(self.props[i].area):
                continue
            karty.append(Karta(self.labely == i, self.props[i].centroid,
                               self))
        self.karty = karty

    # validace obsahu labelu
    def validaceRegionu(self, area):
        return area > self.prah

    # validuj spravne nacteni snimku
    def validaceCesty(self):
        return self.color is not None

    def zaradKarty(self):
        stredy_y = []
        stredy_x = []
        self.hraci = []
        global karty_na_stole
        self.pouzitelne_karty_stul = []  # z techto karet budou pocitany ppsti
        self.pocet_karet = len(self.karty)
        self.pocet_hracu = (self.pocet_karet - 5)/2
        # serad karty podle jejich vysky ve snimku
        karty_serazene = sorted(self.karty, key=lambda karta: karta.y)
        for karta in karty_serazene:
            if karta.vysledek != "pozadi":
                dostupne_karty.remove(str(karta.hodnotaNum) + karta.barva)
                karty_na_stole.append(karta.barva + str(karta.hodnotaNum))
            stredy_y.append(karta.y)
            stredy_x.append(karta.x)
        dif = np.diff(stredy_y)  # rozdil serazenych stredu karet
        posledni_horni = np.where(abs(dif) > 500)[0][0]
        horni_karty = karty_serazene[:posledni_horni+1]
        karty_stul = karty_serazene[posledni_horni+1:posledni_horni+6]
        dolni_karty = karty_serazene[posledni_horni+6:]
        # serazeni podle relativni sirky
        self.horni_karty = sorted(horni_karty, key=lambda karta: karta.x)
        self.karty_stul = sorted(karty_stul, key=lambda karta: karta.x)
        # zakryte karty jsou nalevo a ne napravo - otoc poradi karet
        if (self.karty_stul[0].vysledek == "pozadi" and
                self.karty_stul[-1].vysledek != "pozadi"):
            self.karty_stul.reverse()

        self.pocet_karet_pozadi = sum(k.vysledek == "pozadi" for k in
                                      self.karty_stul)
        if self.pocet_karet_pozadi == 5:
            self.stav_hry = "Pre-Flop"
        elif self.pocet_karet_pozadi == 2:
            self.stav_hry = "Flop"
        elif self.pocet_karet_pozadi == 1:
            self.stav_hry = "Turn"
        elif self.pocet_karet_pozadi == 0:
            self.stav_hry = "River"
        else:
            self.stav_hry = "N/A"
        self.dolni_karty = sorted(dolni_karty, key=lambda karta: karta.x)
        i = 0
        j = 1
        poradi = 1
        hrac_id = 0
        # prirazeni karet hracum
        for karta in self.horni_karty + self.dolni_karty:
            if i % 2 == 0:
                hrac = Hrac(hrac_id, 1)
                hrac.barva = barvy_hracu[hrac_id]
                hrac_id += 1
                self.hraci.append(hrac)
            hrac.karty.append(karta)
            karta.popis = hrac.id
            karta.poradi = poradi
            i += 1
            poradi += 1
        for karta in self.karty_stul:
            if karta.vysledek != "pozadi":
                self.pouzitelne_karty_stul.append(str(karta.hodnotaNum) +
                                                  karta.barva)
            if j < 4:
                karta.popis = 'Flop'
            elif j == 4:
                karta.popis = 'Turn'
            elif j == 5:
                karta.popis = 'River'

            karta.poradi = poradi
            j += 1
            poradi += 1

    # vypis karet na stole
    def vypis(self):
        karty = sorted(self.karty, key=lambda karta: karta.poradi)
        for karta in karty:
            print("%s: %s" % (karta.popis, karta.vysledek))


class Karta:
    def __init__(self, imgLabel, stred, snimek):
        self.label = imgLabel
        self.img = img_as_ubyte(imgLabel)
        self.stred = stred
        self.snimek = snimek
        self.y = stred[0]
        self.x = stred[1]

    def najdiKontury(self):  # nakresli kontury kolem oblasti
        self.kontury, _ = cv2.findContours(self.img, cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_TC89_L1)
        cv2.drawContours(self.img, self.kontury, -1, (255, 0, 0), 1)

    def barevneKontury(self, barva):  # pro barevne rozliseni hracu
        (r, g, b) = barva
        barva = (b, g, r)
        self.kontury, _ = cv2.findContours(self.img, cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_TC89_L1)
        cv2.drawContours(self.snimek.kontury, self.kontury, -1, barva, 15)

    def minBox(self):  # vytvori z kontur minimalni box kolem oblasti
        ctyruhelnik = cv2.minAreaRect(self.kontury[-1])
        (_, _), (self.sirka, self.vyska), _ = ctyruhelnik
        if self.sirka > self.vyska:
            temp = self.sirka
            self.sirka = self.vyska
            self.vyska = temp

        self.sirka = int(self.sirka)
        self.vyska = int(self.vyska)
        box = cv2.boxPoints(ctyruhelnik)
        self.box = np.int0(box)

    def otocBox(self):  # otoci snimek/kartu tak, aby byl/a vodorovne
        minX = self.box[np.argmin(self.box[:, 0])]
        maxY = self.box[np.argmax(self.box[:, 1])]
        self.pocatek = (self.box[1, 0], self.box[2, 1])
        x = float(maxY[0] - minX[0])
        y = float(maxY[1] - minX[1])
        uhel = np.degrees(np.arctan2(y, x))
        if uhel > 45:
            self.uhel = 90 - uhel
        else:
            self.uhel = -uhel
        (h, w) = self.img.shape[:2]
        (cX, cY) = (w // 2, h // 2)

        # matice rotace
        M = cv2.getRotationMatrix2D((cX, cY), uhel, 1.0)

        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])

        # spocteni novych okraju obrazku
        nW = int((h * sin) + (w * cos))
        nH = int((h * cos) + (w * sin))

        # zohledneni translace pri rotaci
        M[0, 2] += (nW / 2) - cX
        M[1, 2] += (nH / 2) - cY

        self.otocenyBox = cv2.warpAffine(self.img, M, (nW, nH))
        self.otocenySnimek = cv2.warpAffine(self.snimek.color, M, (nW, nH))

    def vyjmiKartu(self):  # vyjme kartu ze snimku
        maska = self.otocenyBox > 0
        souradnice = np.argwhere(maska)

        try:
            x0, y0 = souradnice.min(axis=0)
            x1, y1 = souradnice.max(axis=0)
        except ValueError:  # nastane pokud `y` je 0, nevim proc
            pass

        self.orezana_karta = self.otocenySnimek[x0:x1, y0:y1]
        # rotace karty na vysku
        vyska_karty, sirka_karty = self.orezana_karta.shape[:2]
        if vyska_karty < sirka_karty:
            self.orezana_karta = np.rot90(self.orezana_karta)

    def upravRozmer(self):  # resize karty
        karta_sit = cv2.resize(self.orezana_karta, (150, 200),
                               interpolation=cv2.INTER_CUBIC)
        karta_sit = cv2.cvtColor(karta_sit, cv2.COLOR_BGR2RGB)
        # pripraveni karty pro sit
        self.karta_sit = np.expand_dims(karta_sit.astype(float), axis=0)
        self.karta_sit = self.karta_sit/255

    def numerickaHodnota(self):  # upravi A J Q K na 14 11 12 13
        hodnoty_dict = {'A': 14, 'J': 11, 'Q': 12, 'K': 13}
        try:
            self.hodnotaNum = int(self.hodnota)
        except ValueError:
            self.hodnotaNum = hodnoty_dict[self.hodnota]


# tato trida je castecne generovana pomoci programu qt designer, kde bylo
# vytvoreno gui
class Ui_MainWindow(object):
    def spoctiPpsti(self):  # spocti ppsti na vyhru/remizu vsech hracu na stole
        # validace nacteni vsech potrebnych atributu
        popis = ""
        if hasattr(self, 'snimek'):
            if not hasattr(self.snimek, 'pocet_karet_pozadi'):
                return
        else:
            return
        try:  # pokud uzivatel klikne dvakrat po sobe na tlacitko, nedelej nic
            popis = self.table_karty_hraci.item(0, 1).text()
        except AttributeError:
            pass
        else:
            if popis != "":
                return
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        # vsechny karty jsou odkryty - staci vyhodnotit
        if self.snimek.stav_hry == "River":
            pocet_simulaci = 1
        elif self.snimek.stav_hry == "Turn":
            pocet_simulaci = 5000
        else:
            pocet_simulaci = 20000
        for hrac in self.snimek.hraci:  # inicializace poctu her
            hrac.pocet_vyher = 0
            hrac.pocet_remiz = 0
        # simulace hry
        for x in range(0, pocet_simulaci):
            karty_na_stole = self.snimek.pouzitelne_karty_stul.copy()
            remiza = False
            kombinace_stul = dostupne_karty.copy()
            # generace nahodnych karet misto karet s pozadim
            for i in range(0, 5 - len(karty_na_stole)):
                karta = random.sample(kombinace_stul, 1)[0]
                kombinace_stul.remove(karta)
                karty_na_stole.append(karta)
            # vyhodnoceni nejlepsich kombinaci pro jednotlive hrace
            for hrac in self.snimek.hraci:
                hrac.karty_na_stole = karty_na_stole
                hrac.vyhodnotRuce()
            # serazeni hracu od nejlepsiho po nejhorsiho
            serazeni_hraci = sorted(self.snimek.hraci, key=lambda hrac: (
                hrac.nejlepsiRuka.sila, hrac.nejlepsiRuka.nejvyssiHodnota,
                hrac.nejlepsiRuka.suma), reverse=True)
            vyherce = serazeni_hraci[0]  # potencialni vitez
            # zkontrolovani remizy
            for hrac in serazeni_hraci[1:]:
                if (vyherce.nejlepsiRuka.sila == hrac.nejlepsiRuka.sila
                        and vyherce.nejlepsiRuka.nejvyssiHodnota ==
                        hrac.nejlepsiRuka.nejvyssiHodnota
                        and vyherce.nejlepsiRuka.suma ==
                        hrac.nejlepsiRuka.suma):
                    remiza = True
                    hrac.pocet_remiz += 1

            if remiza:
                vyherce.pocet_remiz += 1
            else:
                vyherce.pocet_vyher += 1

        # vypis pravdepodobnosti
        for hrac in self.snimek.hraci:
            item = QtWidgets.QTableWidgetItem()
            pocet_vyher = round(100*hrac.pocet_vyher/pocet_simulaci, 2)
            item.setData(QtCore.Qt.EditRole, pocet_vyher)
            item.setTextAlignment(
                QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            item.setForeground(QtGui.QColor(*hrac.barva))
            item.setFont(font)
            self.table_karty_hraci.setItem(hrac.id, 1,
                                           QtWidgets.QTableWidgetItem(item))
            item = QtWidgets.QTableWidgetItem()
            pocet_remiz = round(100*hrac.pocet_remiz/pocet_simulaci, 2)
            item.setData(QtCore.Qt.EditRole, pocet_remiz)
            item.setTextAlignment(
                QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            item.setForeground(QtGui.QColor(*hrac.barva))
            item.setFont(font)
            self.table_karty_hraci.setItem(hrac.id, 2,
                                           QtWidgets.QTableWidgetItem(item))
        self.table_karty_hraci.setSortingEnabled(True)
        # sort podle nejvyssi ppsti
        self.table_karty_hraci.sortByColumn(1, QtCore.Qt.DescendingOrder)
        QtWidgets.QApplication.restoreOverrideCursor()

    def smazTabulku(self, table):
        self.MainWindow.resize(1005, 580)
        table.setRowCount(0)

    def nahradKartuVeSnimku(self, karta, nahrazena_karta):
        if not hasattr(self.snimek, 'temp'):
            self.snimek.temp = Image.fromarray(
                cv2.cvtColor(self.snimek.kontury, cv2.COLOR_BGR2RGB))
        else:
            self.snimek.temp = Image.fromarray(self.snimek.temp)
        self.snimek.temp.paste(karta.img, nahrazena_karta.pocatek, karta.img)
        self.snimek.temp = np.array(self.snimek.temp)

    def vygenerujNahradniKartu(self, index):
        karty_set = random.randint(1, 3)  # nahodny set karet
        nahrazena_karta = self.snimek.karty_stul[index]
        karta, hodnota, barva = generujNahodnouKartu(karty_set,
                                                     nahrazena_karta.uhel,
                                                     nahrazena_karta.vyska,
                                                     nahrazena_karta.sirka)
        if karta:
            nova_karta = Karta(nahrazena_karta.label,
                               nahrazena_karta.stred,
                               nahrazena_karta.snimek)
            self.snimek.pouzitelne_karty_stul.append(hodnota + barva)
            nova_karta.img = karta
            self.snimek.karty_stul[index] = nova_karta
            self.nahradKartuVeSnimku(nova_karta, nahrazena_karta)
            return hodnoty_str[int(hodnota)-2] + barvy_dict[barva]
        else:
            return ""

    def vymazPpsti(self):
        self.table_karty_hraci.setSortingEnabled(True)
        self.table_karty_hraci.sortByColumn(3, QtCore.Qt.AscendingOrder)
        self.table_karty_hraci.setSortingEnabled(False)
        for hrac in self.snimek.hraci:
            item = QtWidgets.QTableWidgetItem()
            item.setText("")
            item.setData(QtCore.Qt.EditRole, "")
            self.table_karty_hraci.setItem(hrac.id, 1,
                                           QtWidgets.QTableWidgetItem(item))
            self.table_karty_hraci.setItem(hrac.id, 2,
                                           QtWidgets.QTableWidgetItem(item))

    # vygeneruje nahodne karty misto pozadi pro flop, turn, river
    def odkryjKarty(self):
        # byly zamereny karty?
        if self.table_karty_stul.rowCount() == 0:
            return
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        popis = ""
        if self.snimek.stav_hry == "Pre-Flop":
            index = 0
            while index < 3:
                nazev = self.vygenerujNahradniKartu(index)
                if nazev:
                    popis += nazev + " "
                    index += 1
            item = QtWidgets.QTableWidgetItem(popis)
            item.setTextAlignment(
                QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            item.setFont(font)
            self.table_karty_stul.setItem(0, 0, item)
            self.snimek.stav_hry = "Flop"

        elif self.snimek.stav_hry == "Flop":
            while True:
                popis = self.vygenerujNahradniKartu(3)
                if popis:
                    item = QtWidgets.QTableWidgetItem(popis)
                    item.setTextAlignment(
                        QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                    item.setFont(font)
                    self.table_karty_stul.setItem(0, 1, item)
                    break
            self.snimek.stav_hry = "Turn"

        elif self.snimek.stav_hry == "Turn":
            while True:
                popis = self.vygenerujNahradniKartu(4)
                if popis:
                    item = QtWidgets.QTableWidgetItem(popis)
                    item.setTextAlignment(
                        QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                    item.setFont(font)
                    self.table_karty_stul.setItem(
                        0, 2, QtWidgets.QTableWidgetItem(item))
                    break
            self.snimek.stav_hry = "River"
        else:
            QtWidgets.QApplication.restoreOverrideCursor()
            return

        # aktualizace karet na stole pro hrace
        for hrac in self.snimek.hraci:
            hrac.karty_na_stole = self.snimek.karty_stul
        height, width, channel = self.snimek.temp.shape
        bytesPerLine = 3 * width
        img = QtGui.QImage(self.snimek.temp.data, width, height,
                           bytesPerLine, QtGui.QImage.Format_RGB888)
        self.label.setPixmap(QtGui.QPixmap(img))
        self.label.setScaledContents(True)
        self.statusBar.showMessage("Game state: " + self.snimek.stav_hry)
        self.vymazPpsti()
        self.spoctiPpsti()
        QtWidgets.QApplication.restoreOverrideCursor()

    def rozpoznejKarty(self):
        # validace potrebnych atributu
        if hasattr(self, 'sit'):
            if not self.sit.sit_nactena:
                return
        else:
            return
        if not hasattr(self, 'snimek'):
            self.snimek = Snimek("stul_temp.png")
        # pokud uzivatel klikne dvakrat po sobe na tlacitko, nedelej nic
        if self.table_karty_stul.rowCount() != 0:
            return
        global dostupne_karty, barva_stul, font, karty_na_stole
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        dostupne_karty = kombinace.copy()  # zbytek karet v baliku
        self.snimek.segmentace()
        self.snimek.ziskejKarty()
        for karta in self.snimek.karty:
            karta.najdiKontury()
            karta.minBox()
            karta.otocBox()
            karta.vyjmiKartu()
            karta.upravRozmer()
            self.sit.klasifikuj(karta)
        self.snimek.zaradKarty()
        # kontury community karet
        for karta in self.snimek.karty_stul:
            karta.barevneKontury(barva_stul)
        # kontury barevne podle toho o jakeho hrace se jedna
        for hrac in self.snimek.hraci:
            for karta in hrac.karty:
                karta.barevneKontury(hrac.barva)
        # vizualizace obrazku v gui
        img_temp = cv2.cvtColor(self.snimek.kontury, cv2.COLOR_BGR2RGB)
        height, width, channel = img_temp.shape
        bytesPerLine = 3 * width
        img = QtGui.QImage(img_temp.data, width, height,
                           bytesPerLine, QtGui.QImage.Format_RGB888)
        self.label.setPixmap(QtGui.QPixmap(img))
        self.label.setScaledContents(True)

        self.table_karty_stul.insertRow(0)
        # vypis do tabulek
        popis_temp = ""
        for karta in self.snimek.karty_stul:
            if karta.vysledek == "pozadi":
                popis = "?"
            else:
                karty_na_stole.append(karta.barva + karta.hodnota)
                popis = karta.hodnota + barvy_dict[karta.barva]
            if karta.popis == "Flop":
                popis_temp += popis + " "

            elif karta.popis == "Turn":
                item = QtWidgets.QTableWidgetItem(popis_temp)
                item.setTextAlignment(
                    QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                item.setFont(font)
                self.table_karty_stul.setItem(0, 0, item)
                item = QtWidgets.QTableWidgetItem(popis)
                item.setTextAlignment(
                    QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                item.setFont(font)
                self.table_karty_stul.setItem(0, 1, item)
            elif karta.popis == "River":
                item = QtWidgets.QTableWidgetItem(popis)
                item.setTextAlignment(
                    QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                item.setFont(font)
                self.table_karty_stul.setItem(0, 2,
                                              QtWidgets.QTableWidgetItem(item))

        for hrac in self.snimek.hraci:
            popis_temp = ""
            self.table_karty_hraci.insertRow(hrac.id)
            for karta in hrac.karty:
                karty_na_stole.append(karta.barva + karta.hodnota)
                popis_temp += karta.hodnota + barvy_dict[karta.barva] + " "
            item = QtWidgets.QTableWidgetItem(popis_temp)
            item.setTextAlignment(
                QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            item.setFont(font)
            item.setForeground(QtGui.QColor(*hrac.barva))
            self.table_karty_hraci.setItem(hrac.id, 0,
                                           QtWidgets.QTableWidgetItem(item))
            item = QtWidgets.QTableWidgetItem(str(hrac.id))
            self.table_karty_hraci.setItem(hrac.id, 3,
                                           QtWidgets.QTableWidgetItem(item))
        self.table_karty_hraci.setSortingEnabled(False)
        self.statusBar.showMessage("Game state: " + self.snimek.stav_hry)
        QtWidgets.QApplication.restoreOverrideCursor()
        # resize podle poctu hracu
        MainWindow.resize(1005, 660+30*(self.snimek.pocet_hracu+1))

    def nactiSit(self):  # nacteni NS ze slozky
        sit_dialog = QFileDialog.getExistingDirectory(
            None, "Vyber složku", os.getcwd())
        if not sit_dialog:
            return
        try:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            self.sit = Sit(sit_dialog)
        finally:
            self.updateStatusBar()
            QtWidgets.QApplication.restoreOverrideCursor()

    def nactiObrazek(self):  # nacteni realneho obrazku
        obrazek_dialog, _filter = QFileDialog.getOpenFileName(
            None, "Vyber obrázek", None, filter='Obrázky (*.png *.jpeg *.jpg)')
        if not obrazek_dialog:
            return
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        # vizualizace v gui
        global karty_na_stole
        karty_na_stole = []
        self.label.setPixmap(QtGui.QPixmap(obrazek_dialog))
        self.label.setScaledContents(True)
        self.snimek = Snimek(obrazek_dialog)
        self.smazTabulku(self.table_karty_stul)
        self.smazTabulku(self.table_karty_hraci)
        self.updateStatusBar()
        QtWidgets.QApplication.restoreOverrideCursor()

    def updateStatusBar(self):
        if not hasattr(self, 'sit'):
            return
        if self.sit.sit_nactena:
            self.statusBar.showMessage("CNN loaded succesfully")
        else:
            self.statusBar.showMessage("CNN not loaded - load a valid CNN")

    def generujObrazek(self):
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        global karty_na_stole
        karty_na_stole = []
        pocet_hracu = random.randint(2, 6)
        karty_set = random.randint(1, 3)
        stul = Stul(karty_set)
        stul.vygenerujFlopRiverTurn()
        for i in range(0, pocet_hracu):
            hrac = Hrac(i, karty_set)
            hrac.nactiKarty()
            hrac.slucKarty()
            stul.pridej(hrac.img, hrac.souradnice)
        # stul.zmenVelikost(1000, 600)
        stul.uloz()
        self.snimek = Snimek("stul_temp.png")
        self.label.setPixmap(QtGui.QPixmap("stul_temp.png"))
        self.label.setScaledContents(True)
        self.smazTabulku(self.table_karty_stul)
        self.smazTabulku(self.table_karty_hraci)
        self.updateStatusBar()
        QtWidgets.QApplication.restoreOverrideCursor()

    def setupUi(self, MainWindow):  # generovano z .ui souboru
        MainWindow.setObjectName("MainWindow")
        MainWindow.setWindowModality(QtCore.Qt.NonModal)
        MainWindow.resize(1005, 580)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        MainWindow.setMinimumSize(QtCore.QSize(0, 0))
        MainWindow.setMaximumSize(QtCore.QSize(100000, 70000))
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(
            "img/poker_icon.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        MainWindow.setWindowIcon(icon)
        MainWindow.setStatusTip("")
        MainWindow.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(0, 0, 1001, 521))
        self.label.setFrameShape(QtWidgets.QFrame.Box)
        self.label.setLineWidth(2)
        self.label.setText("")
        self.label.setPixmap(QtGui.QPixmap("stul_temp.png"))
        self.label.setScaledContents(True)
        self.label.setObjectName("label")
        self.table_karty_hraci = QtWidgets.QTableWidget(self.centralwidget)
        self.table_karty_hraci.setEnabled(True)
        self.table_karty_hraci.setGeometry(QtCore.QRect(0, 600, 1000, 191))
        self.table_karty_hraci.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table_karty_hraci.setObjectName("table_karty_hraci")
        self.table_karty_hraci.setColumnCount(4)
        self.table_karty_hraci.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.table_karty_hraci.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.table_karty_hraci.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.table_karty_hraci.setHorizontalHeaderItem(2, item)
        self.table_karty_hraci.horizontalHeader().setDefaultSectionSize(300)
        self.table_karty_hraci.horizontalHeader().setMinimumSectionSize(300)
        self.table_karty_hraci.horizontalHeader().setSortIndicatorShown(False)
        self.table_karty_hraci.horizontalHeader().setStretchLastSection(True)
        self.table_karty_hraci.verticalHeader().setStretchLastSection(False)
        self.table_karty_stul = QtWidgets.QTableWidget(self.centralwidget)
        self.table_karty_stul.setEnabled(True)
        self.table_karty_stul.setGeometry(QtCore.QRect(0, 530, 1000, 61))
        self.table_karty_stul.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table_karty_stul.setObjectName("table_karty_stul")
        self.table_karty_stul.setColumnCount(3)
        self.table_karty_stul.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.table_karty_stul.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.table_karty_stul.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.table_karty_stul.setHorizontalHeaderItem(2, item)
        self.table_karty_stul.horizontalHeader().setDefaultSectionSize(300)
        self.table_karty_stul.horizontalHeader().setMinimumSectionSize(300)
        self.table_karty_stul.horizontalHeader().setSortIndicatorShown(True)
        self.table_karty_stul.horizontalHeader().setStretchLastSection(True)
        self.table_karty_stul.verticalHeader().setStretchLastSection(False)
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusBar = QtWidgets.QStatusBar(MainWindow)
        self.statusBar.setObjectName("statusBar")
        MainWindow.setStatusBar(self.statusBar)
        self.toolBar = QtWidgets.QToolBar(MainWindow)
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setStrikeOut(False)
        self.toolBar.setFont(font)
        self.toolBar.setMovable(False)
        self.toolBar.setIconSize(QtCore.QSize(24, 24))
        self.toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toolBar.setFloatable(False)
        self.toolBar.setObjectName("toolBar")
        MainWindow.addToolBar(QtCore.Qt.TopToolBarArea, self.toolBar)
        self.action_nacti_sit = QtWidgets.QAction(MainWindow)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap("img/folder.svg"),
                        QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.action_nacti_sit.setIcon(icon1)
        self.action_nacti_sit.setShortcutVisibleInContextMenu(False)
        self.action_nacti_sit.setObjectName("action_nacti_sit")
        self.action_nacti_obrazek = QtWidgets.QAction(MainWindow)
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap("img/obrazek.svg"),
                        QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.action_nacti_obrazek.setIcon(icon2)
        self.action_nacti_obrazek.setObjectName("action_nacti_obrazek")
        self.action_generuj_obrazek = QtWidgets.QAction(MainWindow)
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap("img/generovany_obrazek.svg"),
                        QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.action_generuj_obrazek.setIcon(icon3)
        self.action_generuj_obrazek.setObjectName("action_generuj_obrazek")
        self.action_rozpoznej_karty = QtWidgets.QAction(MainWindow)
        icon4 = QtGui.QIcon()
        icon4.addPixmap(QtGui.QPixmap("img/karty.svg"),
                        QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.action_rozpoznej_karty.setIcon(icon4)
        self.action_rozpoznej_karty.setObjectName("action_rozpoznej_karty")
        self.action_spocti_pravdepodobnosti = QtWidgets.QAction(MainWindow)
        icon5 = QtGui.QIcon()
        icon5.addPixmap(QtGui.QPixmap("img/poker.svg"),
                        QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.action_spocti_pravdepodobnosti.setIcon(icon5)
        self.action_spocti_pravdepodobnosti.setObjectName(
            "action_spocti_pravdepodobnosti")
        self.action_odkryj_karty = QtWidgets.QAction(MainWindow)
        icon6 = QtGui.QIcon()
        icon6.addPixmap(QtGui.QPixmap("img/oko.svg"),
                        QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.action_odkryj_karty.setIcon(icon6)
        self.action_odkryj_karty.setObjectName(
            "action_odkryj_karty")
        self.toolBar.addAction(self.action_nacti_sit)
        self.toolBar.addAction(self.action_nacti_obrazek)
        self.toolBar.addAction(self.action_generuj_obrazek)
        self.toolBar.addAction(self.action_rozpoznej_karty)
        self.toolBar.addAction(self.action_odkryj_karty)
        self.toolBar.addAction(self.action_spocti_pravdepodobnosti)
        self.statusBar.showMessage("Load net")
        self.action_nacti_sit.triggered.connect(self.nactiSit)
        self.action_nacti_obrazek.triggered.connect(self.nactiObrazek)
        self.action_generuj_obrazek.triggered.connect(self.generujObrazek)
        self.action_rozpoznej_karty.triggered.connect(self.rozpoznejKarty)
        self.action_odkryj_karty.triggered.connect(self.odkryjKarty)
        self.action_spocti_pravdepodobnosti.triggered.connect(
            self.spoctiPpsti)
        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        self.MainWindow = MainWindow

    def retranslateUi(self, MainWindow):  # generovano z .ui souboru
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Poker"))
        item = self.table_karty_hraci.horizontalHeaderItem(0)
        item.setText(_translate("MainWindow", "Cards"))
        item = self.table_karty_hraci.horizontalHeaderItem(1)
        item.setText(_translate("MainWindow", "Win probability [%]"))
        item = self.table_karty_hraci.horizontalHeaderItem(2)
        item.setText(_translate("MainWindow", "Draw probability [%]"))
        self.table_karty_hraci.setColumnHidden(3, True)
        self.table_karty_stul.setSortingEnabled(True)
        item = self.table_karty_stul.horizontalHeaderItem(0)
        item.setText(_translate("MainWindow", "Flop"))
        item = self.table_karty_stul.horizontalHeaderItem(1)
        item.setText(_translate("MainWindow", "Turn"))
        item = self.table_karty_stul.horizontalHeaderItem(2)
        item.setText(_translate("MainWindow", "River"))
        self.toolBar.setWindowTitle(_translate("MainWindow", "toolBar"))
        self.action_nacti_sit.setText(_translate("MainWindow", "Load net"))
        self.action_nacti_sit.setToolTip(_translate(
            "MainWindow", "choose the folder CNN-cards"))
        self.action_nacti_obrazek.setText(
            _translate("MainWindow", "Load image"))
        self.action_nacti_obrazek.setToolTip(
            _translate("MainWindow", "Some sample images are in the folder "
                       + "\"sample_images\""))
        self.action_generuj_obrazek.setText(
            _translate("MainWindow", "Generate random image"))
        self.action_generuj_obrazek.setToolTip(
            _translate("MainWindow", "Synthetic random image"))
        self.action_rozpoznej_karty.setText(
            _translate("MainWindow", "Identify"))
        self.action_rozpoznej_karty.setToolTip(_translate(
            "MainWindow", "Identifies all the cards on the image and assigns"
            + " them to players"))
        self.action_odkryj_karty.setText(
            _translate("MainWindow", "Next step"))
        self.action_odkryj_karty.setToolTip(
            _translate("MainWindow", "Simulates the next game state"))
        self.action_spocti_pravdepodobnosti.setText(
            _translate("MainWindow", "Compute probabilities"))
        self.action_spocti_pravdepodobnosti.setToolTip(_translate(
            "MainWindow", "Probabilities of win and draw for every player"))


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    app.setStyleSheet(qdarkstyle.load_stylesheet())  # tmavy styl GUI
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
