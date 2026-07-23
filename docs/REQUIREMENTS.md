# Requirements

## Cel projektu

Celem projektu jest stworzenie pomocniczej aplikacji sprzedażowej działającej lokalnie na Raspberry Pi. Aplikacja ma ułatwiać sprzedaż warzyw i owoców przez szybkie wybieranie produktów, liczenie ceny, liczenie reszty oraz zapisywanie historii sprzedaży.

Aplikacja nie jest certyfikowaną kasą fiskalną.

## Środowisko docelowe

- Raspberry Pi,
- ekran HDMI,
- klawiatura USB albo klawiatura numeryczna,
- opcjonalnie myszka,
- docelowo możliwa integracja z wagą elektroniczną,
- lokalna baza SQLite,
- praca offline.

## Środowisko developerskie

- Windows albo Linux,
- Python 3.11+,
- PySide6 jako docelowe GUI,
- SQLite,
- pytest,
- ruff,
- mypy,
- mock wagi zamiast prawdziwego sprzętu.

## Wymagania funkcjonalne

### Produkty

Aplikacja musi umożliwiać:

- synchronizowanie produktów z pliku `config/products.csv`,
- dodawanie i aktualizowanie produktów przez stabilne pole `code`,
- dezaktywowanie produktów przez `active=false`,
- ustawianie ceny produktu,
- ustawianie jednostki produktu: kilogramy albo sztuki,
- ustawianie kolejności wyświetlania produktów,
- przypisywanie nazwy pliku ikony,
- wyświetlanie aktywnych produktów jako przycisków w GUI.

Produkt zawiera:

- `id`,
- `code`,
- `name`,
- `unit_type`,
- `price_grosze`,
- `active`,
- `sort_order`,
- `icon_filename`.

Plik CSV zawiera kolumny:

- `code`,
- `name`,
- `unit`,
- `price_grosze`,
- `active`,
- `sort_order`,
- `icon_filename`.

Przed zapisem cały plik jest walidowany. `code` musi być niepusty i unikalny,
`unit` może mieć wartość `kg` albo `szt`, cena musi być większa od zera,
`active` ma wartość `true` albo `false`, a `sort_order` jest nieujemną liczbą
całkowitą.

Synchronizacja wykonuje transakcyjny upsert po `code`. Produkt nieobecny w CSV
jest fizycznie usuwany z tabeli `products`. Wartość `active=false` zachowuje
produkt w bazie, ale ukrywa go na ekranie sprzedaży. Grafiki produktów znajdują
się w `assets/products`; brak wskazanego pliku zastępuje `fallback.png`.

### Koszyk

Aplikacja musi umożliwiać:

- dodawanie produktu ważonego z aktualnej wagi,
- dodawanie produktu na sztuki z podaną ilością,
- usuwanie ostatniej pozycji,
- czyszczenie koszyka,
- wyświetlanie pozycji koszyka,
- liczenie sumy technicznej,
- liczenie sumy końcowej po zaokrągleniu.

Pozycja koszyka zawiera snapshot danych produktu:

- `product_id`,
- `product_name_snapshot`,
- `unit_type_snapshot`,
- `unit_price_grosze_snapshot`,
- `quantity_value`,
- `line_total_grosze`.

Dla kilogramów `quantity_value` oznacza gramy.

Dla sztuk `quantity_value` oznacza liczbę sztuk.

### Produkty ważone

Dla produktów sprzedawanych na kilogramy:

- waga jest reprezentowana jako `int` w gramach,
- cena jest reprezentowana jako `int` w groszach za kilogram,
- wartość pozycji jest liczona bez `float`.

Przykład:

```text
cena: 450 gr/kg
waga: 2300 g
wartość: 1035 gr
```

### Produkty na sztuki

Dla produktów sprzedawanych na sztuki:

- ilość jest liczbą całkowitą,
- cena jest reprezentowana jako `int` w groszach za sztukę,
- wartość pozycji = cena za sztukę × ilość.

### Pieniądze

W całym projekcie pieniądze są reprezentowane jako `int` w groszach.

Nie wolno używać `float` ani `double` do reprezentacji pieniędzy.

Poprawne:

```text
42,50 zł = 4250
```

Niepoprawne:

```text
42.50 jako float
```

`core/money.py` zawiera tylko czystą logikę obliczeń. Nie formatuje tekstów i nie parsuje tekstu użytkownika.

### Zaokrąglanie

Suma końcowa jest zaokrąglana do najbliższych 50 groszy.

Przykłady:

```text
42,24 zł -> 42,00 zł
42,25 zł -> 42,50 zł
42,49 zł -> 42,50 zł
42,50 zł -> 42,50 zł
42,74 zł -> 42,50 zł
42,75 zł -> 43,00 zł
```

Aplikacja przechowuje:

- sumę techniczną przed zaokrągleniem,
- sumę końcową po zaokrągleniu.

### Płatność

Aplikacja musi umożliwiać:

- rozpoczęcie płatności tylko dla niepustego koszyka,
- wpisanie kwoty otrzymanej od klienta,
- sprawdzenie, czy kwota otrzymana jest wystarczająca,
- wyliczenie reszty albo brakującej kwoty,
- zapis sprzedaży po zaakceptowanej płatności.

`set_paid_grosze()` działa tylko po jawnie rozpoczętej płatności.

### Historia sprzedaży

Aplikacja musi zapisywać każdą zakończoną sprzedaż.

Sprzedaż zawiera:

- identyfikator,
- datę i godzinę,
- sumę techniczną,
- sumę po zaokrągleniu,
- kwotę otrzymaną,
- resztę,
- pozycje sprzedaży.

Pozycje sprzedaży zawierają snapshot danych produktu, aby późniejsza zmiana ceny albo nazwy nie zmieniała historii.

Snapshot pozycji sprzedaży zawiera:

- `product_code_snapshot`,
- `product_name_snapshot`,
- `unit_snapshot`,
- `unit_price_grosze_snapshot`.

`sale_items.product_id` jest opcjonalnym powiązaniem technicznym. Klucz obcy
używa `ON DELETE SET NULL`, nigdy `ON DELETE CASCADE`. Raporty historyczne
identyfikują produkt przez `product_code_snapshot`, więc usunięcie produktu
z `products` nie usuwa ani nie zmienia pozycji sprzedaży.

GUI historii nie może operować bezpośrednio na `Sale` ani `SaleItem`. Ma korzystać z DTO:

- `SaleSummaryViewState`,
- `SaleDetailsViewState`,
- `SaleItemViewState`.

### Baza danych

Aplikacja używa SQLite.

Wymagane tabele MVP:

- `products`,
- `sales`,
- `sale_items`.

Nie używać ORM w MVP. Preferowane jest `sqlite3` z biblioteki standardowej.

Zapis sprzedaży musi być transakcyjny: jeśli zapis pozycji się nie uda, rekord sprzedaży nie zostaje w bazie.

Synchronizacja produktów również musi być transakcyjna: walidacja całego CSV
odbywa się przed zapisem, a wszystkie operacje `INSERT`, `UPDATE` i `DELETE`
wchodzą do jednej transakcji.

### Mock wagi

Na etapie developmentu aplikacja działa bez prawdziwej wagi.

Wymagany jest interfejs `Scale` oraz implementacja `MockScale`.

Mock wagi umożliwia:

- ustawienie masy testowej w gramach,
- odczyt masy w gramach,
- reset/tarowanie wartości.

Docelowa implementacja prawdziwej wagi ma zostać dodana później jako osobny adapter.

### GUI

Aplikacja ma GUI w PySide6.

Aktualnie główna nawigacja udostępnia:

- ekran sprzedaży.

GUI ma korzystać z publicznej fasady `AppController` i DTO/ViewState. GUI nie powinno importować:

- `core.Product`,
- `core.UnitType`,
- `core.Cart`,
- `core.CartItem`,
- `core.Sale`,
- `core.SaleItem`.

GUI nie importuje modułu synchronizacji CSV ani repozytoriów. Konfiguracja
produktów jest synchronizowana przed utworzeniem kontrolera i okna aplikacji.

Wszystkie teksty widoczne w GUI powinny być przygotowane w warstwie `controller/presentation`, przede wszystkim przez `ViewState` i stałe z `controller/labels.py`.

### Obsługa klawiaturą

Aplikacja musi obsługiwać skróty klawiaturowe.

Skróty klawiaturowe muszą wywoływać te same akcje co przyciski GUI.

Poprawny model:

```text
GUI button -> command/controller -> ViewState
keyboard   -> command/controller -> ViewState
```

Niepoprawny model:

```text
GUI button ma własną logikę sprzedaży
keyboard ma osobną skopiowaną logikę sprzedaży
```

`Command.SELECT_PRODUCT` przyjmuje `product_id`. Skrót klawiaturowy `1-9` oznacza slot przycisku produktu i jest mapowany do `product_id` przez `ProductViewState`.

### Eksport danych

MVP może nie zawierać eksportu, ale architektura powinna umożliwiać późniejsze dodanie:

- eksportu CSV,
- backupu bazy danych,
- eksportu historii sprzedaży.

## Wymagania niefunkcjonalne

### Niezawodność

Aplikacja ma być prosta, przewidywalna i odporna na błędy operatora.

Wymagane:

- walidacja kwoty otrzymanej,
- walidacja ilości,
- walidacja ceny produktu,
- brak ujemnych kwot,
- brak sprzedaży pustego koszyka,
- brak zapisu sprzedaży bez zatwierdzonej płatności.

### Testowalność

Czysta logika domenowa musi być testowalna bez GUI, bazy danych i sprzętu.

Testy obejmują:

- obliczenia pieniędzy,
- zaokrąglanie do 50 groszy,
- liczenie reszty,
- liczenie pozycji ważonej,
- liczenie pozycji na sztuki,
- sumowanie koszyka,
- tworzenie sprzedaży,
- repozytoria SQLite,
- transakcyjność zapisu sprzedaży,
- mock wagi,
- DTO/ViewState,
- fasadę `AppController`,
- `KeyboardController`.

Formatowanie tekstów UI jest testowane poza `core/money.py`.

### Rozdzielenie odpowiedzialności

`core/` nie może importować:

- `ui/`,
- `data/`,
- `hardware/`,
- `controller/`.

`ui/` nie powinno importować `core/` ani zawierać logiki liczenia sprzedaży.

`hardware/` nie powinno zawierać logiki sprzedaży.

`data/` nie powinno zawierać logiki GUI.

`controller/` jest miejscem integracji domeny, repozytoriów, sprzętu i DTO dla GUI.

### Offline-first

Aplikacja musi działać bez internetu.

Internet nie może być wymagany do:

- sprzedaży,
- edycji produktów,
- liczenia ceny,
- zapisu historii.

### Prostota

Nie dodawać frameworków bez potrzeby.

Na etapie MVP unikać:

- ORM,
- web backendu,
- kont użytkowników,
- synchronizacji chmurowej,
- rozbudowanego systemu uprawnień,
- integracji fiskalnych,
- drukarki,
- rozbicia reszty na nominały.

Poza zakresem MVP:

- certyfikacja fiskalna,
- drukowanie paragonów fiskalnych,
- integracja z terminalem płatniczym,
- synchronizacja z chmurą,
- obsługa wielu stanowisk jednocześnie,
- rozbudowane raporty księgowe,
- zarządzanie magazynem,
- obsługa kodów kreskowych,
- skaner,
- logowanie użytkowników.
