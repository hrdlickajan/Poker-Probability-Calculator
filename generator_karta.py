from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import os

font_cesta = 'fonts/pismo.TTF'
font_cesta2 = 'fonts/pismo2.ttf'
barvy = ['S', 'H', 'D', 'C']
cerne_barvy = ['S', 'C']
hodnoty = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
hodnoty_s_obrazkem = ['J', 'Q', 'K']
slozka_obrazky = 'obrazky_ke_kartam/'
cesta_karty = 'karty/'
karty_na_stole = []


def vytvorSlozku(cesta):  # vytvor slozku pokud neexistuje
    if not os.path.exists(cesta):
        os.makedirs(cesta)


def validaceHodnoty(hodnota_karty):
    if hodnota_karty not in hodnoty:
        print('Hodnota karty nebyla spravne zadana')
        return False
    else:
        return True


def validaceBarvy(cesta, barva):
    if not os.path.exists(cesta) or barva not in barvy:
        print('Barva karty se nenachazi ve slozce suits')
        return False
    else:
        return True


class Font:
    def __init__(self, barva_karty, hodnota_karty):
        self.hodnota_karty = hodnota_karty
        # barva pisma se ridi podle barvy/znaku
        if barva_karty in cerne_barvy:
            self.barva = (0, 0, 0)
        else:
            self.barva = (255, 0, 0)

        if hodnota_karty == '10':
            self.font = ImageFont.truetype(font_cesta2, 100)
        else:
            self.font = ImageFont.truetype(font_cesta, 100)


class Karta:
    # ciselne hodnoty zvoleny namerenim realne karty a experimantalne
    def __init__(self, hodnota, barva, cesta_barva, vyska, sirka, rotace,
                 cesta_karta, font, karty_set):
        self.original_y = 880
        self.original_x = 630
        self.hodnota = hodnota
        self.resized_y = vyska
        self.resized_x = sirka
        self.rotace = rotace
        self.barva = barva
        if karty_set in [2, 3] or hodnota == 'pozadi':
            return
        if self.hodnota in ['Q', 'K']:
            self.offset_pismo_x = 25
            self.offset_pismo_x_P = self.original_x - 85
        else:
            self.offset_pismo_x = 30
            self.offset_pismo_x_P = self.original_x - 90
        self.offset_pismo_y = 15
        self.offset_znak_y = 140
        self.offset_znak_x = 37
        self.barva_mala_x = 51
        self.barva_mala_y = 70
        self.barva_JQK_x = 110
        self.barva_JQK_y = 110
        self.barva_x = 140
        self.barva_y = 140
        self.stred_x = (self.original_x - self.barva_x) // 2
        self.stred_y = (self.original_y - self.barva_y) // 2
        self.dvojice_x = self.barva_x//2 + 30
        self.dvojice_y = self.barva_y//2 + 10
        self.horni_y = self.barva_y//2 + 150
        self.dvojice_horni_y = self.barva_y//2 + 200
        self.dvojice_x_P = self.original_x - (3*self.barva_x)//2 - 30
        self.JQK_x = self.barva_JQK_x//2 + 50
        self.JQK_y = self.barva_JQK_y//2 + 45
        self.offset_znak_x_P = self.original_x - 80

        self.obrazek_x = self.original_x-186
        self.obrazek_y = self.original_y-166
        self.barva_img = Image.open(cesta_barva).resize((self.barva_x,
                                                         self.barva_y),
                                                        Image.ANTIALIAS)
        self.barva_img_JQK = Image.open(cesta_barva).resize((self.barva_JQK_x,
                                                             self.barva_JQK_y),
                                                            Image.ANTIALIAS)
        self.barva_img_mensi = self.barva_img.resize((self.barva_mala_x,
                                                      self.barva_mala_y),
                                                     Image.ANTIALIAS)

        self.img = Image.new('RGB', (self.original_x, self.original_y),
                             (255, 255, 255))
        self.cesta = cesta_karta
        self.pismo = font
        if hodnota in hodnoty_s_obrazkem:
            self.vykresleniObdelnika()
            self.nacteniObrazku()

    # zaobleni rohy karty
    def zaobliRohy(self):
        w = self.original_x
        h = self.original_y
        rad = 40  # radius
        circle = Image.new('L', (rad * 2, rad * 2), 0)
        draw = ImageDraw.Draw(circle)
        draw.ellipse((0, 0, rad * 2, rad * 2), fill=255)
        alpha = Image.new('L', (w, h), 255)
        alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
        alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
        alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
        alpha.paste(circle.crop((rad, rad, rad * 2, rad * 2)),
                    (w - rad, h - rad))
        self.img.putalpha(alpha)

    # nacteni JQK obrazku pro vlozeni
    def nacteniObrazku(self):
        self.obrazek = Image.open(slozka_obrazky + self.barva + self.hodnota
                                  + '.png').resize((self.obrazek_x,
                                                    self.obrazek_y))

    # vlozi nacteny JQK obrazek do karty
    def vykresleniObrazku(self):
        offset_x = 93
        offset_y = 83
        self.img.paste(self.obrazek, (offset_x, offset_y,
                                      offset_x + self.obrazek_x,
                                      offset_y + self.obrazek_y))

    def vykresleniOkraju(self):
        self.vykresleniHornihoOkraje()
        self.img = self.img.rotate(180)
        self.vykresleniHornihoOkraje()
        self.img = self.img.rotate(180)

    # vykresli okraj kolem karty - hodnotu a maly znak
    def vykresleniHornihoOkraje(self):
        self.vykresleniHodnoty(self.offset_pismo_x,
                               self.offset_pismo_y)

        self.vykresleniHodnoty(self.offset_pismo_x_P,
                               self.offset_pismo_y)

        self.vykresleniHorniBarvy(self.offset_znak_x,
                                  self.offset_znak_y)

        self.vykresleniHorniBarvy(self.offset_znak_x_P,
                                  self.offset_znak_y)

    # vykresli hodnotu karty
    def vykresleniHodnoty(self, offset_x, offset_y):
        draw = ImageDraw.Draw(self.img)
        draw.text((offset_x, offset_y), self.hodnota,
                  self.pismo.barva, font=self.pismo.font)

    # vykresli znaky v horni polovine karty
    def vykresleniHorniBarvy(self, offset_x, offset_y):
        self.img.paste(self.barva_img_mensi, (offset_x, offset_y,
                                              offset_x + self.barva_mala_x,
                                              offset_y + self.barva_mala_y))

    # vykresli obdelnik kolem obrazku (JQK)
    def vykresleniObdelnika(self):
        draw = ImageDraw.Draw(self.img)
        draw.rectangle(((90, 80), (self.original_x-90, self.original_y-80)),
                       outline="blue", width=3)

    def vykresleni(self):
        # vykresli prostredni znak
        if self.hodnota in ['3', '5', '9', 'A']:
            self.vykresleniJednohoZnaku(self.stred_x, self.stred_y)
        # vykresli horni a dolni dvojici znaku
        if self.hodnota in ['4', '5', '6', '7', '8', '9', '10']:
            self.vykresleniJednohoZnaku(self.dvojice_x, self.dvojice_y)
            self.vykresleniJednohoZnaku(self.dvojice_x_P, self.dvojice_y)
            self.img = self.img.rotate(180)
            self.vykresleniJednohoZnaku(self.dvojice_x, self.dvojice_y)
            self.vykresleniJednohoZnaku(self.dvojice_x_P, self.dvojice_y)
            self.img = self.img.rotate(180)
        # vykresli horni a dolni prostredni znak
        if self.hodnota in ['2', '3']:
            self.vykresleniJednohoZnaku(self.stred_x, self.dvojice_y)
            self.img = self.img.rotate(180)
            self.vykresleniJednohoZnaku(self.stred_x, self.dvojice_y)
            self.img = self.img.rotate(180)
        # vykresli 2 prostredni znaky
        if self.hodnota in ['7', '6', '8']:
            self.vykresleniJednohoZnaku(self.dvojice_x, self.stred_y)
            self.vykresleniJednohoZnaku(self.dvojice_x_P, self.stred_y)
        # vykresli horni prostredni znak
        if self.hodnota in ['7', '8', '10']:
            self.vykresleniJednohoZnaku(self.stred_x, self.horni_y)
            if self.hodnota in ['8', '10']:
                self.img = self.img.rotate(180)
                self.vykresleniJednohoZnaku(self.stred_x, self.horni_y)
                self.img = self.img.rotate(180)
        # vykresli horni prostreni dvojici znaku
        if self.hodnota in ['9', '10']:
            self.vykresleniJednohoZnaku(self.dvojice_x, self.dvojice_horni_y)
            self.vykresleniJednohoZnaku(self.dvojice_x_P, self.dvojice_horni_y)
            self.img = self.img.rotate(180)
            self.vykresleniJednohoZnaku(self.dvojice_x, self.dvojice_horni_y)
            self.vykresleniJednohoZnaku(self.dvojice_x_P, self.dvojice_horni_y)
            self.img = self.img.rotate(180)
        # vykresli barvu do rohu pro kluka damu a krale
        if self.hodnota in ['J', 'Q', 'K']:
            self.vykresleniJednohoZnaku(self.JQK_x, self.JQK_y)
            self.img = self.img.rotate(180)
            self.vykresleniJednohoZnaku(self.JQK_x, self.JQK_y)
            self.img = self.img.rotate(180)

    def vykresleniJednohoZnaku(self, x, y):
        if self.hodnota not in ['J', 'Q', 'K']:
            self.img.paste(self.barva_img, (x, y, x + self.barva_x, y
                                            + self.barva_y))
        else:
            self.img.paste(self.barva_img_JQK, (x, y, x + self.barva_JQK_x, y
                                                + self.barva_JQK_y))

    # rotuj kartu do zvolene cesty
    def rotuj(self):
        resized = self.img.resize((self.resized_x, self.resized_y),
                                  Image.ANTIALIAS)
        rotated_temp = resized.rotate(self.rotace, expand=1,
                                      resample=Image.NEAREST)
        self.rotated = Image.new("RGBA", (rotated_temp.size[0],
                                          rotated_temp.size[1]), (0, 0, 0, 0))
        rot = self.img.rotate(self.rotace,
                              expand=1).resize(rotated_temp.size)
        self.rotated.paste(rot, (0, 0), rot)
        self.rotated.save("asdasddad.png")

    # resize karty s ohledem na transparanetnost - radius v rohach
    def zmenaVelikosti(self):
        img = self.img.convert("RGBA")    # konverze na RGBA kanaly
        img.load()
        bands = img.split()
        bands = [b.resize((self.resized_x, self.resized_y),
                          Image.ANTIALIAS) for b in bands]
        self.resized = Image.merge('RGBA', bands)


def vytvorKartu(karty_set, rotace, hodnota, barva, vyska, sirka,
                cesta_karta=""):
    cesta_barva = 'suits/' + barva + '.png'
    hodnota = hodnoty[int(hodnota)-2]  # prepocet hodnoty
    # validace spravnosti zadanych argumentu
    if not (validaceHodnoty(hodnota) and validaceBarvy(cesta_barva, barva)):
        return

    font = Font(barva, hodnota)
    karta = Karta(hodnota, barva, cesta_barva, vyska, sirka, rotace,
                  cesta_karta, font, karty_set)

    if karty_set in [2, 3]:
        cesta = str(karty_set) + '/' + barva + hodnota + '.png'
        karta.img = Image.open(cesta)

        karta.zmenaVelikosti()
        karta.rotuj()

    else:
        if hodnota in hodnoty_s_obrazkem:
            karta.vykresleniObrazku()

        karta.vykresleni()
        karta.vykresleniOkraju()
        karta.zaobliRohy()
        karta.zmenaVelikosti()
        karta.rotuj()
    return karta.rotated


# vytvori kartu otocenou pozadim nahoru
def vytvorPozadi(karty_set, rotace):
    karta = Karta('pozadi', None, None, 528, 378, rotace,
                  None, None, karty_set)
    cesta = str(karty_set) + '/' + 'pozadi' + '.png'
    karta.img = Image.open(cesta).convert("RGBA").resize((630, 880),
                                                         Image.ANTIALIAS)
    karta.zmenaVelikosti()
    karta.zaobliRohy()
    karta.rotuj()
    return karta.rotated
