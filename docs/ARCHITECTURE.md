## `docs/ARCHITECTURE.md`

# Architecture

## Przegląd

Projekt jest lokalną aplikacją desktopową w Pythonie, uruchamianą docelowo na Raspberry Pi z ekranem HDMI.

Aplikacja używa:

- PySide6 do GUI
- SQLite do lokalnej bazy danych
- czystej logiki domenowej w `core/`
- adapterów sprzętowych w `hardware/`
- kontrolerów aplikacyjnych w `controller/`

Główna zasada architektury:

core nie wie nic o GUI, bazie danych ani sprzęcie

## Warstwy
ui/
  PySide6 widgets, okna, ekrany

controller/
  obsługa komend użytkownika, maszyna stanów aplikacji

core/
  logika domenowa: pieniądze, produkty, koszyk, sprzedaż

data/
  SQLite, repozytoria, zapis/odczyt

hardware/
  waga, mock wagi, przyszłe urządzenia zewnętrzne
## Kierunek zależności

Dozwolone zależności:

ui -> controller
controller -> core
controller -> data
controller -> hardware
data -> core
hardware -> core lub brak zależności

Niedozwolone zależności:

core -> ui
core -> data
core -> hardware
data -> ui
hardware -> ui

## Struktura katalogów
src/
  cash_assistant/
    __init__.py
    main.py

    core/
      __init__.py
      money.py
      product.py
      cart.py
      sale.py

    data/
      __init__.py
      database.py
      product_repository.py
      sale_repository.py

    hardware/
      __init__.py
      scale.py
      mock_scale.py

    controller/
      __init__.py
      app_controller.py
      keyboard_controller.py
      view_state.py

    ui/
      __init__.py
      formatters.py
      main_window.py
      sales_screen.py
      settings_screen.py
      history_screen.py

## Moduł core

core zawiera czystą logikę domenową.

Nie wolno tutaj importować PySide6, sqlite3, GPIO ani klas GUI.

money.py

Odpowiedzialność:

- czysta logika obliczeń na pieniądzach reprezentowanych jako `int` w groszach
- liczenie wartości pozycji ważonej
- liczenie wartości pozycji na sztuki
- zaokrąglanie końcowej kwoty
- liczenie reszty

Wymagane funkcje:

def calculate_weighted_line_total_grosze(
    unit_price_grosze: int,
    weight_grams: int,
) -> int:
    ...

def calculate_piece_line_total_grosze(
    unit_price_grosze: int,
    quantity: int,
) -> int:
    ...

def round_to_nearest_50_grosze(amount_grosze: int) -> int:
    ...

def calculate_change(paid_grosze: int, total_grosze: int) -> int:
    ...

Zasady:

- wejściem i wyjściem są liczby całkowite w groszach
- waga jest reprezentowana jako `int` w gramach
- nie używać float
- nie formatować tekstów dla GUI
- nie parsować tekstów wpisywanych przez użytkownika
- błędne dane wejściowe powinny zgłaszać ValueError

Formatowanie pieniędzy i ilości do tekstów widocznych w GUI nie należy do `core/money.py`.
Teksty dla GUI są przygotowywane poza `core`, w warstwie prezentacji/kontrolera oraz pomocniczo
w `ui/formatters.py`.

product.py

Odpowiedzialność:

- reprezentacja produktu
- jednostka sprzedaży
- cena

Przykładowe typy:

from dataclasses import dataclass
from enum import Enum


class UnitType(Enum):
    KG = "kg"
    PIECE = "piece"


@dataclass(frozen=True)
class Product:
    id: int | None
    name: str
    unit_type: UnitType
    price_grosze: int
    active: bool = True
    sort_order: int = 0

cart.py

Odpowiedzialność:

- pozycje koszyka
- dodawanie pozycji
- usuwanie pozycji
- czyszczenie koszyka
- liczenie sumy technicznej
- liczenie sumy końcowej

Pozycja koszyka musi przechowywać snapshot produktu:

@dataclass(frozen=True)
class CartItem:
    product_id: int | None
    product_name_snapshot: str
    unit_type_snapshot: UnitType
    unit_price_grosze_snapshot: int
    quantity_value: int
    line_total_grosze: int

Dla kilogramów quantity_value oznacza gramy.

Dla sztuk quantity_value oznacza liczbę sztuk.

sale.py

Odpowiedzialność:

- reprezentacja zakończonej sprzedaży
- dane zapisywane do historii
- pozycje sprzedaży

Sprzedaż powinna przechowywać:

- datę i godzinę
- sumę techniczną
- sumę po zaokrągleniu
- kwotę otrzymaną
- resztę
- pozycje sprzedaży

Moduł data

data odpowiada za SQLite.

Na etapie MVP nie używać ORM.

database.py

Odpowiedzialność:

- otwarcie połączenia SQLite
- inicjalizacja schematu
- migracje MVP, jeśli będą potrzebne
- transakcje

Minimalny schemat:

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    unit_type TEXT NOT NULL,
    price_grosze INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    raw_total_grosze INTEGER NOT NULL,
    rounded_total_grosze INTEGER NOT NULL,
    paid_grosze INTEGER NOT NULL,
    change_grosze INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sale_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL,
    product_id INTEGER,
    product_name_snapshot TEXT NOT NULL,
    unit_type_snapshot TEXT NOT NULL,
    unit_price_grosze_snapshot INTEGER NOT NULL,
    quantity_value INTEGER NOT NULL,
    line_total_grosze INTEGER NOT NULL,
    FOREIGN KEY (sale_id) REFERENCES sales(id)
);

## Repozytoria

Repozytoria izolują resztę aplikacji od SQL.

Wymagane repozytoria MVP:

ProductRepository
SaleRepository

ProductRepository:

- list active products
- list all products
- create product
- update product
- deactivate product

SaleRepository:

- save sale
- list recent sales
- read sale details

Moduł hardware

hardware odpowiada za sprzęt.

Na początku wymagany jest tylko mock wagi.

scale.py

Interfejs wagi:

from abc import ABC, abstractmethod


class Scale(ABC):
    @abstractmethod
    def get_weight_grams(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def tare(self) -> None:
        raise NotImplementedError

mock_scale.py

Mock wagi:

class MockScale(Scale):
    def __init__(self) -> None:
        self._weight_grams = 0

    def set_weight_grams(self, weight_grams: int) -> None:
        if weight_grams < 0:
            raise ValueError("weight_grams cannot be negative")
        self._weight_grams = weight_grams

    def get_weight_grams(self) -> int:
        return self._weight_grams

    def tare(self) -> None:
        self._weight_grams = 0

Docelowo można dodać:

real_scale.py

ale nie implementować go w MVP bez konkretnego modelu wagi.

Moduł controller

controller odpowiada za logikę aplikacyjną i przejścia między stanami.

controller przygotowuje dane dla GUI w postaci prostych DTO/ViewState.
GUI nie powinno samodzielnie składać danych domenowych ani formatować jednostek na podstawie `UnitType`.
Przykładowe DTO:

- `ProductViewState`
- `CartItemViewState`
- `ViewState`

Produkty przekazywane do GUI powinny zawierać gotowe pola tekstowe:

- `product_id`
- `name`
- `price_text`
- `unit_text`
- `button_text`

Stany aplikacji

Minimalne stany:

PRODUCT_SELECTION
ENTERING_QUANTITY
READING_WEIGHT
CART_REVIEW
PAYMENT
SETTINGS
HISTORY
Komendy

GUI i klawiatura powinny generować te same komendy.

Przykładowe komendy:

SELECT_PRODUCT
DIGIT_TYPED
DECIMAL_SEPARATOR_TYPED
CONFIRM
CANCEL
BACKSPACE
REMOVE_LAST_ITEM
CLEAR_CART
START_PAYMENT
SAVE_SALE
OPEN_SETTINGS
OPEN_HISTORY
Zasada

Nie wolno pisać osobnej logiki dla kliknięcia GUI i osobnej logiki dla klawisza.

Poprawnie:

button click -> command -> controller
key press    -> command -> controller

Niepoprawnie:

button click -> jedna ścieżka logiki
key press    -> druga skopiowana ścieżka logiki

## Moduł ui

ui odpowiada za PySide6.

ui odpowiada za wyświetlanie i zdarzenia użytkownika.
Nie powinno importować `core/` ani znać modeli domenowych takich jak `Product`, `CartItem`,
`Sale` czy `UnitType`.

Ekrany GUI powinny dostawać gotowy `ViewState` z `controller/` i emitować komendy do kontrolera.

formatters.py

Odpowiedzialność:

- proste formatowanie prymitywów do tekstów UI, np. groszy, gramów, ilości sztuk
- brak zależności od `core/`

Przykłady:

def format_money(grosze: int) -> str:
    ...

def format_weight_grams(weight_grams: int) -> str:
    ...

def format_piece_quantity(quantity: int) -> str:
    ...

def format_unit_price(price_grosze: int, unit_text: str) -> str:
    ...

Formatowanie wymagające znajomości `UnitType` powinno być wykonane w warstwie
controller/presentation, np. podczas budowania `ProductViewState` lub `CartItemViewState`.

main_window.py

Główne okno aplikacji.

Odpowiedzialność:

- tworzy główny layout
- przełącza ekrany
- przekazuje zdarzenia do kontrolera
- odświeża widok na podstawie stanu aplikacji

sales_screen.py

Ekran sprzedaży.

Pokazuje:

- przyciski produktów
- koszyk
- sumę techniczną
- sumę po zaokrągleniu
- kwotę otrzymaną
- resztę
- aktualny tryb

settings_screen.py

Ekran ustawień produktów.

Pozwala:

- dodać produkt
- edytować produkt
- zmienić cenę
- zmienić jednostkę
- dezaktywować produkt

history_screen.py

Ekran historii.

Pokazuje:

- ostatnie sprzedaże
- szczegóły sprzedaży
- sumy
- pozycje

## Obsługa klawiatury

PySide6 może obsługiwać skróty przez:

- QShortcut
- QAction
- keyPressEvent
- eventFilter

Dla aplikacji sprzedażowej preferowany jest centralny handler klawiatury, ponieważ znaczenie klawiszy zależy od aktualnego stanu.

Przykład:

Klawisz 1:
- w PRODUCT_SELECTION wybiera produkt nr 1
- w ENTERING_QUANTITY dopisuje cyfrę 1
- w PAYMENT dopisuje cyfrę 1 do kwoty otrzymanej

## Testowanie
### Testy jednostkowe

Wymagane dla:

- money.py
- cart.py
- sale.py

### Testy bez sprzętu

Cała logika MVP musi działać bez Raspberry Pi i bez prawdziwej wagi.

Na komputerze developerskim używany jest MockScale.

### Testy bazy

Repozytoria powinny być testowane na tymczasowej bazie SQLite.

## Decyzje architektoniczne

Dlaczego Python?
- szybki development
- dobra współpraca z Codexem
- dobry ekosystem dla SQLite, GUI i Raspberry Pi
- wystarczająca wydajność dla aplikacji sprzedażowej

Dlaczego PySide6?
- pełne GUI desktopowe
- dobre wsparcie skrótów klawiaturowych
- możliwość działania fullscreen
- lepszy wygląd i większa elastyczność niż Tkinter

Dlaczego SQLite?
- lokalna baza
- brak serwera
- stabilność
- prostota backupu
- wystarczające dla jednego stanowiska

Dlaczego mock wagi?
- umożliwia development na PC
- izoluje sprzęt od logiki
- pozwala testować aplikację bez Raspberry Pi
- ułatwia późniejszą wymianę adaptera sprzętowego

Zasady dla Codexa

Codex powinien pracować etapami.

Nie generować całej aplikacji naraz.

Preferowana kolejność:

1. szkielet projektu
2. testy dla money.py
3. implementacja money.py
4. modele domenowe
5. testy cart.py
6. implementacja cart.py
7. SQLite schema
8. repozytoria
9. mock wagi
10. podstawowe GUI
11. obsługa klawiatury
12. ekran ustawień
13. historia sprzedaży

Dla logiki domenowej preferować test-first.

Dla GUI dopuszczalny jest prototype-first.
