# Cash Assistant

Pomocnicza aplikacja sprzedażowa na Raspberry Pi do obsługi sprzedaży warzyw i owoców.

Aplikacja ma działać lokalnie, offline, z ekranem HDMI oraz obsługą przez myszkę i skróty klawiaturowe. Docelowo może współpracować z wagą elektroniczną, ale na etapie developmentu używany jest mock wagi.

## Główne założenia

- Python 3.11+
- PySide6 jako GUI
- SQLite jako lokalna baza danych
- aplikacja offline-first
- obsługa przez GUI oraz skróty klawiaturowe
- mock wagi na komputerze developerskim
- docelowo Raspberry Pi + ekran HDMI
- pieniądze reprezentowane jako `int` w groszach
- waga reprezentowana jako `int` w gramach
- bez używania `float` do pieniędzy
- suma końcowa zaokrąglana do najbliższych 50 groszy
- historia sprzedaży zapisywana lokalnie

## Czego aplikacja nie robi

To nie jest certyfikowana kasa fiskalna. Aplikacja służy jako pomocniczy kalkulator i rejestr sprzedaży. Nie zastępuje urządzenia fiskalnego, jeżeli przepisy wymagają jego użycia.

## Funkcje MVP

- lista produktów z cenami
- produkty sprzedawane na kilogramy albo sztuki
- dodawanie produktów do koszyka
- liczenie wartości pozycji
- liczenie sumy koszyka
- zaokrąglanie kwoty końcowej do 0,50 zł
- wpisanie kwoty otrzymanej od klienta
- wyliczenie reszty
- zapis sprzedaży do SQLite
- historia sprzedaży
- edycja produktów i cen
- mock wagi
- obsługa skrótów klawiaturowych

## Przykładowy workflow sprzedaży

1. Operator wybiera produkt przyciskiem GUI albo skrótem klawiaturowym.
2. Dla produktu ważonego aplikacja pobiera wagę z mocka albo z prawdziwej wagi.
3. Dla produktu sprzedawanego na sztuki operator wpisuje ilość.
4. Produkt trafia do koszyka.
5. Operator dodaje kolejne produkty.
6. Aplikacja pokazuje sumę techniczną i kwotę po zaokrągleniu.
7. Operator wpisuje kwotę otrzymaną od klienta.
8. Aplikacja pokazuje resztę.
9. Sprzedaż jest zapisywana w historii.

## Instalacja developerska

bash:

python -m venv .venv

Windows:

.venv\Scripts\activate

Linux / Raspberry Pi:

source .venv/bin/activate

Instalacja zależności:

pip install -e ".[dev]"

Uruchomienie aplikacji:

cash-assistant

Albo:

python -m cash_assistant.main

Uruchomienie testów:

pytest

Formatowanie kodu:

ruff format .

Lint:

ruff check .

Type-checking:

mypy src

Struktura projektu:

cash_assistant/
  pyproject.toml
  README.md

  docs/
    REQUIREMENTS.md
    ARCHITECTURE.md

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

      ui/
        __init__.py
        main_window.py
        sales_screen.py
        settings_screen.py
        history_screen.py

  tests/
    test_money.py
    test_cart.py
    test_sale.py

Zasady projektowe:
- core/ nie może importować ui/, data/ ani hardware/.
- core/ zawiera czystą logikę domenową.
- ui/ odpowiada za wyświetlanie i zdarzenia użytkownika.
- controller/ tłumaczy akcje UI/klawiatury na operacje aplikacji.
- data/ odpowiada za SQLite.
- hardware/ odpowiada za wagę i przyszłe urządzenia zewnętrzne.
- Logika pieniędzy musi być testowana jednostkowo.
- Pieniądze zawsze są liczone jako liczby całkowite w groszach.
- Waga zawsze jest liczona jako liczba całkowita w gramach.
- Nie wolno używać float do pieniędzy.
- Skróty klawiaturowe — założenie MVP

Docelowa mapa może się zmienić, ale MVP zakłada:

1-9       wybór produktu albo wpisywanie liczby zależnie od trybu
0         cyfra 0
. / ,     separator dziesiętny przy wpisywaniu wartości
+         dodaj / zatwierdź pozycję
Enter     OK / zatwierdź
Backspace usuń ostatni znak
Esc       anuluj aktualną operację
F1        ustawienia produktów
F2        historia sprzedaży
F5        odśwież / powrót do sprzedaży

Znaczenie klawiszy zależy od aktualnego stanu aplikacji.

Tryby aplikacji
PRODUCT_SELECTION — wybór produktu
ENTERING_QUANTITY — wpisywanie ilości sztuk
READING_WEIGHT — pobieranie wagi
CART_REVIEW — podgląd koszyka
PAYMENT — wpisywanie kwoty otrzymanej
SETTINGS — edycja produktów i cen
HISTORY — historia sprzedaży
