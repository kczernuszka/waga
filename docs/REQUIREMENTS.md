## `docs/REQUIREMENTS.md`

# Requirements

## Cel projektu

Celem projektu jest stworzenie pomocniczej aplikacji sprzedażowej działającej na Raspberry Pi. Aplikacja ma ułatwiać sprzedaż warzyw i owoców przez szybkie wybieranie produktów, liczenie ceny, liczenie reszty oraz zapisywanie historii sprzedaży.

Aplikacja nie jest certyfikowaną kasą fiskalną.

## Środowisko docelowe

- Raspberry Pi
- ekran HDMI
- klawiatura USB lub klawiatura numeryczna
- opcjonalnie myszka
- docelowo możliwa integracja z wagą elektroniczną
- lokalna baza SQLite
- praca offline

## Środowisko developerskie

- Windows albo Linux
- Python 3.11+
- PySide6
- SQLite
- pytest
- mock wagi zamiast prawdziwego sprzętu

## Wymagania funkcjonalne

### Produkty

Aplikacja musi umożliwiać:

- dodawanie produktów
- edycję produktów
- dezaktywowanie produktów
- ustawianie ceny produktu
- ustawianie jednostki produktu:
  - kilogramy
  - sztuki
- ustawianie kolejności wyświetlania produktów
- wyświetlanie produktów jako przycisków w GUI

Produkt musi mieć co najmniej:

- identyfikator
- nazwę
- jednostkę sprzedaży
- cenę w groszach
- status aktywności
- kolejność sortowania

### Koszyk

Aplikacja musi umożliwiać:

- dodawanie produktu do koszyka
- usuwanie ostatniej pozycji
- czyszczenie koszyka
- wyświetlanie pozycji koszyka
- liczenie sumy technicznej
- liczenie sumy końcowej po zaokrągleniu

Pozycja koszyka musi zawierać:

- produkt
- nazwę produktu w momencie sprzedaży
- cenę produktu w momencie sprzedaży
- jednostkę produktu w momencie sprzedaży
- ilość albo wagę
- wartość pozycji w groszach

### Produkty ważone

Dla produktów sprzedawanych na kilogramy:

- waga musi być reprezentowana jako `int` w gramach
- cena musi być reprezentowana jako `int` w groszach za kilogram
- wartość pozycji musi być liczona bez używania `float`

Przykład:

cena: 450 gr/kg
waga: 2300 g
wartość: 1035 gr

### Produkty na sztuki

Dla produktów sprzedawanych na sztuki:

- ilość musi być liczbą całkowitą
- cena musi być reprezentowana jako int w groszach za sztukę
- wartość pozycji = cena za sztukę × ilość

### Pieniądze

W całym projekcie pieniądze muszą być reprezentowane jako int w groszach.

Nie wolno używać float ani double do reprezentacji pieniędzy.

Poprawne:

42,50 zł = 4250

Niepoprawne:

42.50 jako float

### Zaokrąglanie

Suma końcowa musi być zaokrąglana do najbliższych 50 groszy.

Przykłady:

42,24 zł -> 42,00 zł
42,25 zł -> 42,50 zł
42,49 zł -> 42,50 zł
42,50 zł -> 42,50 zł
42,74 zł -> 42,50 zł
42,75 zł -> 43,00 zł

Aplikacja powinna przechowywać:

- sumę techniczną przed zaokrągleniem
- sumę końcową po zaokrągleniu

### Płatność

Aplikacja musi umożliwiać:

- wpisanie kwoty otrzymanej od klienta
- sprawdzenie, czy kwota otrzymana jest wystarczająca
- wyliczenie reszty
- pokazanie reszty jako kwoty w złotówkach

Aplikacja nie musi pokazywać rozbicia reszty na nominały.

### Historia sprzedaży

Aplikacja musi zapisywać każdą zakończoną sprzedaż.

Sprzedaż musi zawierać:

- identyfikator
- datę i godzinę
- sumę techniczną
- sumę po zaokrągleniu
- kwotę otrzymaną
- resztę
- pozycje sprzedaży

Pozycje sprzedaży muszą zawierać snapshot danych produktu, aby późniejsza zmiana ceny nie zmieniała historii.

### Baza danych

Aplikacja musi używać SQLite.

Wymagane tabele MVP:

- products
- sales
- sale_items

Nie używać ORM w MVP. Preferowane jest sqlite3 z biblioteki standardowej.

### Mock wagi

Na etapie developmentu aplikacja musi działać bez prawdziwej wagi.

Wymagany jest interfejs Scale oraz implementacja MockScale.

Mock wagi musi umożliwiać:

- ustawienie masy testowej w gramach
- odczyt masy w gramach
- reset wartości

Docelowa implementacja prawdziwej wagi ma zostać dodana później jako osobny adapter.

### GUI

Aplikacja musi mieć GUI w PySide6.

Wymagane ekrany MVP:

- ekran sprzedaży
- ekran ustawień produktów
- ekran historii sprzedaży

Ekran sprzedaży musi pokazywać:

- przyciski produktów
- aktualny koszyk
- sumę techniczną
- sumę po zaokrągleniu
- kwotę otrzymaną
- resztę
- aktualny tryb aplikacji

### Obsługa klawiaturą

Aplikacja musi obsługiwać skróty klawiaturowe.

Skróty klawiaturowe muszą wywoływać te same akcje co przyciski GUI.

Logika nie może być duplikowana między kliknięciami GUI i skrótami klawiaturowymi.

Poprawny model:

GUI button -> command -> controller
keyboard   -> command -> controller

Niepoprawny model:

GUI button ma własną logikę
keyboard ma osobną skopiowaną logikę

### Eksport danych

MVP może nie zawierać eksportu, ale architektura powinna umożliwiać późniejsze dodanie:

- eksportu CSV
- backupu bazy danych
- eksportu historii sprzedaży

## Wymagania niefunkcjonalne
### Niezawodność

Aplikacja ma być prosta, przewidywalna i odporna na błędy operatora.

Wymagane:

walidacja kwoty otrzymanej
walidacja ilości
walidacja ceny produktu
brak ujemnych kwot
brak sprzedaży pustego koszyka
brak zapisu sprzedaży bez zatwierdzenia

### Testowalność

Czysta logika domenowa musi być testowalna bez GUI, bazy danych i sprzętu.

Testy jednostkowe są wymagane dla:

- formatowania pieniędzy
- parsowania pieniędzy
- zaokrąglania do 50 groszy
- liczenia reszty
- liczenia pozycji ważonej
- liczenia pozycji na sztuki
- sumowania koszyka

### Rozdzielenie odpowiedzialności

core/ nie może importować:

- ui/
- data/
- hardware/

ui/ nie powinno zawierać logiki liczenia sprzedaży.

hardware/ nie powinno zawierać logiki sprzedaży.

data/ nie powinno zawierać logiki GUI.

### Offline-first

Aplikacja musi działać bez internetu.

Internet nie może być wymagany do:

- sprzedaży
- edycji produktów
- liczenia ceny
- zapisu historii

### Prostota

Nie dodawać frameworków bez potrzeby.

Na etapie MVP unikać:

- ORM
- web backendu
- kont użytkowników
- synchronizacji chmurowej
- rozbudowanego systemu uprawnień
- integracji fiskalnych
- drukarki
- rozbicia reszty na nominały

Poza zakresem MVP:

- certyfikacja fiskalna
- drukowanie paragonów fiskalnych
- integracja z terminalem płatniczym
- synchronizacja z chmurą
- obsługa wielu stanowisk jednocześnie
- rozbudowane raporty księgowe
- zarządzanie magazynem
- obsługa kodów kreskowych
- skaner
- logowanie użytkowników
