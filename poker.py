import tkinter as tk
from tkinter import filedialog  # , Text
import scipy.ndimage as ndimage
from skimage import img_as_ubyte
from PIL import ImageTk, Image
import skimage.measure
from skimage.filters import threshold_otsu
import os
import numpy as np
import itertools
import random
import cv2
import tensorflow as tf
import pickle
import generator_stul
from tensorflow.keras.models import Sequential

canvas_height = 800
canvas_width = 1000

barvy_dict = {"S": "♠", "C": "♣", "H": "♥", "D": "♦"}
hodnoty = list(range(2, 15))
barvy = ["C", "S", "H", "D"]
kombinace = set()
for barva in barvy:
    for hodnota in hodnoty:
        kombinace.add(str(hodnota) + barva)


class Snimek:
    # nacti snimek
    def __init__(self, snimek_cesta):
        self.color = cv2.imread(snimek_cesta)
        self.img_tk = ImageTk.PhotoImage(Image.open(
            snimek_cesta).resize((canvas_width,
                                  canvas_height-200),
                                 Image.ANTIALIAS))
        self.gray = cv2.imread(snimek_cesta, 0)
        self.kontury = cv2.imread(snimek_cesta)
        self.nazev_snimku = os.path.basename(os.path.splitext(snimek_cesta)[0])

    # segmentace pomoci otsu, labeling a mereni regionu
    def segmentace(self):
        prah = threshold_otsu(self.gray)
        self.segmentovany = self.gray > prah
        imgEr = ndimage.binary_erosion(self.segmentovany,
                                       iterations=1).astype(np.int)
        # self.labely = skimage.measure.label(img_gray_thresh, background=0)
        self.labely = skimage.measure.label(imgEr, background=0)
        self.props = skimage.measure.regionprops(self.labely + 1)
        self.nastavPrah()

    def nastavPrah(self):  # todo udelat lip?
        # obsahy = []
        # for i in range(1, np.max(self.labely)):
        #     obsahy.append(self.props[i].area)
        # self.prah = sorted(obsahy)[-13]
        self.prah = 30000

    # zkontroluje obsah labelu a pokud je obsah dostatecny, jedna se o kartu
    def ziskejKarty(self):
        karty = []
        for i in range(1, np.max(self.labely)+1):

            if not self.validaceRegionu(self.props[i].area):
                continue
            karty.append(Karta(self.labely == i, self.props[i].centroid,
                               self))
        self.karty = karty

    def validaceRegionu(self, area):
        if area < self.prah:
            return False
        else:
            return True

    # validuj spravne nacteni snimku
    def validaceCesty(self):
        return self.color is not None

    def zaradKarty(self):
        stredy_y = []
        stredy_x = []
        self.hraci = []
        self.pouzitelne_karty_stul = []
        self.pocet_karet = len(self.karty)
        self.pocet_hracu = (self.pocet_karet - 5)/2
        # serad karty podle jejich vysky
        karty_serazene = sorted(self.karty, key=lambda karta: karta.y)
        for karta in karty_serazene:
            if karta.vysledek != "pozadi":
                dostupne_karty.remove(str(karta.hodnotaNum) + karta.barva)
            stredy_y.append(karta.y)
            stredy_x.append(karta.x)
        dif = np.diff(stredy_y)
        posledni_horni = np.where(abs(dif) > 500)[0][0]
        horni_karty = karty_serazene[:posledni_horni+1]
        karty_stul = karty_serazene[posledni_horni+1:posledni_horni+6]
        dolni_karty = karty_serazene[posledni_horni+6:]
        self.horni_karty = sorted(horni_karty, key=lambda karta: karta.x)
        self.karty_stul = sorted(karty_stul, key=lambda karta: karta.x)
        if (self.karty_stul[0].vysledek == "pozadi" and
                self.karty_stul[-1].vysledek != "pozadi"):
            self.karty_stul.reverse()

        self.pocet_karet_pozadi = sum(k.vysledek == "pozadi" for k in
                                      self.karty_stul)
        if self.pocet_karet_pozadi == 5:
            self.stav_hry = "PreFlop"
        elif self.pocet_karet_pozadi == 2:
            self.stav_hry = "Flop"
        elif self.pocet_karet_pozadi == 1:
            self.stav_hry = "Turn"
        elif self.pocet_karet_pozadi == 0:
            self.stav_hry = "River"
        else:
            self.stav_hry = "Neznamy"
        self.dolni_karty = sorted(dolni_karty, key=lambda karta: karta.x)
        i = 0
        j = 1
        poradi = 1
        hrac_id = 1
        for karta in self.horni_karty + self.dolni_karty:
            if i % 2 == 0:
                hrac = Hrac(hrac_id)
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
                karta.popis = 'River'
            elif j == 5:
                karta.popis = 'Turn'

            karta.poradi = poradi
            j += 1
            poradi += 1

    def vypis(self):
        karty = sorted(self.karty, key=lambda karta: karta.poradi)
        for karta in karty:
            print("%s: %s" % (karta.popis, karta.vysledek))
        # hraci = sorted(self.hraci,
        #                key=lambda hrac: (hrac.nejlepsiRuka.sila,
        #                                  hrac.nejlepsiRuka.nejvyssiHodnota,
        #                                  hrac.nejlepsiRuka.suma),
        # reverse = True)
        # print("\nSerazeni podle sily")
        # for hrac in hraci:
        #     print ("Hrac %s: %s - %s" %
        #            (hrac.id,
        #             hrac.nejlepsiRuka.vysledky, hrac.nejlepsiRuka.popis))

    def getKonturyTk(self):
        img = cv2.cvtColor(self.kontury, cv2.COLOR_BGR2RGB)
        self.img_kontury_tk = ImageTk.PhotoImage(
            Image.fromarray(img).resize(
                (canvas_width, canvas_height-200), Image.ANTIALIAS))
        return self.img_kontury_tk


class Sit:
    # nacti sit pomoci cest k parametrum
    def __init__(self, model_cesta):
        self.sit = Sequential()
        self.sit = tf.keras.models.load_model(model_cesta)
        self.nacti_poradi()

    def nacti_poradi(self):  # nacti pickle soubor s poradim karet
        pickle_in = open("poradi_new.pickle", "rb")
        poradi = pickle.load(pickle_in)
        self.key_list = list(poradi.keys())
        self.val_list = list(poradi.values())

    def klasifikuj(self, karta):
        prediction = self.sit.predict(karta.karta_sit)
        # print(np.argmax(prediction), max(max(prediction)), prediction)
        vysledek = self.key_list[self.val_list.index(np.argmax(prediction))]
        # vysledek = prediction.argmax(axis=-1)
        karta.vysledek = vysledek
        if vysledek == "pozadi":
            karta.barva = "X"
            karta.hodnota = "X"
            karta.numerickaHodnota = 0
        else:
            karta.barva = vysledek[0]
            karta.hodnota = vysledek[1:]
            karta.numerickaHodnota()


class Karta:
    def __init__(self, imgLabel, stred, snimek):
        self.img = img_as_ubyte(imgLabel)
        self.snimek = snimek
        self.y = stred[0]
        self.x = stred[1]

    # ulozi kartu do slozky 'karty' s nazvem snimku v jejim jmenu
    def najdiKontury(self):  # nakresli kontury kolem oblasti
        self.kontury, _ = cv2.findContours(self.img, cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_TC89_L1)
        cv2.drawContours(self.img, self.kontury, -1, (255, 0, 0), 1)

        cv2.drawContours(self.snimek.kontury, self.kontury, -1,
                         (0, 0, 255), 10)

    def minBox(self):  # vytvori z kontur minimalni box kolem oblasti
        ctyruhelnik = cv2.minAreaRect(self.kontury[-1])
        box = cv2.boxPoints(ctyruhelnik)
        self.box = np.int0(box)

    def otocBox(self):  # otoci snimek/kartu tak, aby byl/a vodorovne
        minX = self.box[np.argmin(self.box[:, 0])]
        maxY = self.box[np.argmax(self.box[:, 1])]
        x = float(maxY[0] - minX[0])
        y = float(maxY[1] - minX[1])
        uhel = np.degrees(np.arctan2(y, x))

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
        except ValueError:  # nastane pokud `y` je 0.
            pass

        self.orezana_karta = self.otocenySnimek[x0:x1, y0:y1]
        # rotace karty na vysku
        vyska_karty, sirka_karty = self.orezana_karta.shape[:2]
        if vyska_karty < sirka_karty:
            self.orezana_karta = np.rot90(self.orezana_karta)

    def upravRozmer(self):
        karta_sit = cv2.resize(self.orezana_karta, (150, 200),
                               interpolation=cv2.INTER_CUBIC)
        karta_sit = cv2.cvtColor(karta_sit, cv2.COLOR_BGR2RGB)
        # x = karta_sit.img_to_array(karta_sit)
        self.karta_sit = np.expand_dims(karta_sit.astype(float), axis=0)
        self.karta_sit = self.karta_sit/255

    def numerickaHodnota(self):  # upravi A J Q K na 14 11 12 13
        hodnoty_dict = {'A': 14, 'J': 11, 'Q': 12, 'K': 13}
        try:
            self.hodnotaNum = int(self.hodnota)
        except ValueError:
            self.hodnotaNum = hodnoty_dict[self.hodnota]


class Vizualizace:
    def __init__(self):
        # inicializace GUI - tlacitka, ramecky...
        self.root = tk.Tk()
        self.root.geometry("1000x800")
        self.root.title("Poker")
        self.root.resizable(0, 0)
        self.sit_nactena = tk.BooleanVar()
        self.canvas = tk.Canvas(self.root, height=canvas_height,
                                width=canvas_width, bd=-2)
        self.canvas.pack()
        self.frame = tk.Frame(self.root)
        self.frame.place(relwidth=1, relheight=0.05, rely=0.75)

        self.frame_karty = tk.Frame(self.root)
        self.frame_karty.place(relwidth=1, relheight=0.03, rely=0.87)
        self.frame_karty_stul = tk.Frame(self.root)
        self.frame_karty_stul.place(relwidth=1, relheight=0.05, rely=0.82)
        self.frame_ppsti = tk.Frame(self.root)
        self.frame_ppsti.place(relwidth=1, relheight=0.03, rely=0.9)
        self.sit_button = tk.Button(self.frame, text="Načti síť", padx=5,
                                    pady=5, bg="black", fg="white",
                                    command=self.nactiSit)
        self.sit_button.pack(side="left")

        self.check_button = tk.Checkbutton(self.frame, text="Síť načtena",
                                           state=tk.DISABLED, bg="black",
                                           fg="white", padx=5, pady=5,
                                           variable=self.sit_nactena)
        self.check_button.pack(side="left")

        self.obrazek_button = tk.Button(self.frame, text="Načti obrázek",
                                        padx=5, pady=5, bg="black", fg="white",
                                        command=self.nactiSnimek)
        self.obrazek_button.pack(side="left")

        self.gen_obrazek_button = tk.Button(self.frame,
                                            text="Generuj náhodný obrázek",
                                            padx=5, pady=5, bg="black",
                                            fg="white",
                                            command=self.generujSnimek)
        self.gen_obrazek_button.pack(side="left")

        self.rozpoznej_button = tk.Button(self.frame, text="Rozpoznej karty",
                                          padx=5, pady=5, bg="black",
                                          fg="white",
                                          command=self.ziskejKarty)
        self.rozpoznej_button.pack(side="left")

        self.ppsti_button = tk.Button(self.frame,
                                      text="Spočti pravděpodobnosti na výhru",
                                      padx=5, pady=5, bg="black",
                                      fg="white",
                                      command=self.spoctiPpsti)
        self.ppsti_button.pack(side="left")

        # pri spusteni gui se zobrazi vygenerovany obrazek
        stul = generator_stul.main()
        self.snimek = Snimek("stul_temp.png")
        self.obrazek = tk.Label(self.canvas, image=stul.img_tk)
        self.obrazek.image = stul.img_tk  # reference
        self.obrazek.pack()

    # smaz vsechny objekty v dane oblasti
    def smazPredchozi(self, objekt, rodic):
        if objekt:
            for widget in rodic.winfo_children():
                widget.destroy()

    # nacti model ze zvolene slozky
    def nactiSit(self):
        sit_dialog = filedialog.askdirectory(initialdir=os.getcwd(),
                                             title="Vyber složku")
        try:
            if sit_dialog:
                self.sit = Sit(sit_dialog)
        finally:
            self.sit_nactena.set(self.sit is not None)

    # nacti obrazek a zobraz ho v canvasu
    def nactiSnimek(self):
        obrazek_dialog = filedialog.askopenfile(initialdir=os.getcwd(),
                                                title="Vyber obrázek",
                                                filetypes=[(
                                                    "Obrázky",
                                                    "*.png;*.jpg;*.jpeg")])
        self.smazPredchozi(obrazek_dialog, self.canvas)
        self.smazPredchozi(obrazek_dialog, self.frame_karty)
        self.smazPredchozi(obrazek_dialog, self.frame_karty_stul)
        self.smazPredchozi(obrazek_dialog, self.frame_ppsti)

        self.snimek = Snimek(obrazek_dialog.name)

        self.obrazek = tk.Label(self.canvas, image=self.snimek.img_tk)
        self.obrazek.image = self.snimek.img_tk  # reference
        self.obrazek.pack()

    # vygeneruj nahodny snimek 2-6 hracu, nahodny stav hry, nahodny set
    def generujSnimek(self):
        self.smazPredchozi(self.obrazek, self.canvas)
        self.smazPredchozi(1, self.frame_karty)
        self.smazPredchozi(1, self.frame_karty_stul)
        self.smazPredchozi(1, self.frame_ppsti)
        generator_stul.main()  # skript ulozi obrazek do "stul_temp.png"
        self.snimek = Snimek("stul_temp.png")
        self.obrazek = tk.Label(self.canvas, image=self.snimek.img_tk)
        self.obrazek.image = self.snimek.img_tk  # reference
        self.obrazek.pack()

    # ziskej karty v aktualnim snimku - segmentace, kontury, klasifikace...
    def ziskejKarty(self):
        global dostupne_karty
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

        self.smazPredchozi(self.obrazek, self.canvas)
        self.smazPredchozi(1, self.frame_karty)
        self.smazPredchozi(1, self.frame_karty_stul)
        self.smazPredchozi(1, self.frame_ppsti)

        img_kontury = self.snimek.getKonturyTk()
        self.obrazek = tk.Label(self.canvas, image=img_kontury)
        self.obrazek.image = img_kontury  # reference
        self.obrazek.pack()

        self.snimek.zaradKarty()
        # vypis - jaky hrac ma jake karty
        for hrac in self.snimek.hraci:
            karty_popis = tk.Label(self.frame_karty,
                                   text="Hráč " + str(hrac.id) + ": ")
            karty_popis.pack(side="left")
            for karta in hrac.karty:
                barva = "black"
                # zmen barvu fontu pokud je karta cervena
                if "H" in karta.barva or "D" in karta.barva:
                    barva = "red"
                popis = karta.hodnota + barvy_dict[karta.barva]
                karty_popis = tk.Label(self.frame_karty, text=popis,
                                       font=("Helvetica", 14, "bold"),
                                       fg=barva)
                karty_popis.pack(side="left")
            karty_popis = tk.Label(self.frame_karty, text="    ",
                                   font=("Helvetica", 14), fg=barva)
            karty_popis.pack(side="left")

        karty_popis = tk.Label(self.frame_karty_stul,
                               text="Karty na stole:", padx=2)
        karty_popis.pack(side="left")
        # vypis karet na stole
        for karta in self.snimek.karty_stul:
            barva = "black"
            if "H" in karta.barva or "D" in karta.barva:
                barva = "red"
            if karta.vysledek == "pozadi":
                popis = "?"
            else:
                popis = karta.hodnota + barvy_dict[karta.barva]
            karty_popis = tk.Label(self.frame_karty_stul, text=popis,
                                   font=("Helvetica", 14, "bold"),
                                   fg=barva)
            karty_popis.pack(side="left")

    # vypocet pravdepodobnosti pro vsechny pritomne hrace
    # karty protivniku jsou videt
    def spoctiPpsti(self):
        # vsechny karty jsou odkryty - staci vyhodnotit
        if self.snimek.pocet_karet_pozadi == 0:
            pocet_simulaci = 1
        # river
        elif self.snimek.pocet_karet_pozadi == 1:
            pocet_simulaci = 5000
        else:
            pocet_simulaci = 20000
        for hrac in self.snimek.hraci:
            hrac.pocet_vyher = 0
            hrac.pocet_remiz = 0
        # simulace hry
        for x in range(0, pocet_simulaci):
            karty_na_stole = self.snimek.pouzitelne_karty_stul.copy()
            remiza = False
            kombinace_stul = dostupne_karty.copy()
            # generace nahodnych karet misto karet s pozadim
            for i in range(0, 5 - len(self.snimek.pouzitelne_karty_stul)):
                karta = random.sample(kombinace_stul, 1)[0]
                kombinace_stul.remove(karta)
                karty_na_stole.append(karta)

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
        self.smazPredchozi(1, self.frame_ppsti)
        # vypis pravdepodobnosti
        for hrac in self.snimek.hraci:
            text_ppsti = ("{0:.2f}".format(100*hrac.pocet_vyher/pocet_simulaci)
                          + "/" + "{0:.2f}".format(
                          100*hrac.pocet_remiz/pocet_simulaci) + " %")
            vypln = (21-len(text_ppsti)) * " "
            karty_popis = tk.Label(self.frame_ppsti,
                                   text=text_ppsti + vypln,
                                   font=("Helvetica", 12))
            karty_popis.pack(side="left")


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

    def zkontrolujStraight(self):
        ruka = set(self.hodnoty)
        pet_ruznych_hodnot = len(ruka) == len(self.hodnoty)
        po_sobe_jdouci = max(ruka) - min(ruka) == len(ruka) - 1
        self.straight = pet_ruznych_hodnot and po_sobe_jdouci
        return self.straight or ruka == set([2, 3, 4, 5, 14])  # 14 - eso

    def zkontrolujOpakovaniHodnoty(self):  # par, trojice, ctverice
        # spocita kolikrat se kazdy element vyskytuje v dane ruce
        suma = sum(self.hodnoty.count(r) for r in self.hodnoty)
        # 5 karet - 5 cisel, cislo - kolikrat se hodnota vyskytuje v ruce
        self.ctverice = suma == 17
        self.full_house = suma == 13
        self.trojice = suma == 11
        self.dva_pary = suma == 9
        self.par = suma == 7

    def vyhodnotSilu(self):
        if self.straight and self.flush and self.nejvyssiHodnota == 14:
            self.sila = 9
        elif self.straight and self.flush:
            self.sila = 9
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
            self.sila = 1


class Hrac:
    pocet_vyher = 0
    pocet_remiz = 0

    def __init__(self, id):
        self.id = id
        self.karty = []
        self.karty_na_stole = []

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

        self.nejlepsiRuka = sorted(self.ruce,
                                   key=lambda ruka: (ruka.sila,
                                                     ruka.nejvyssiHodnota,
                                                     ruka.suma)
                                   )[-1]


def main():
    vizualizace = Vizualizace()
    vizualizace.root.mainloop()


if __name__ == "__main__":
    main()
