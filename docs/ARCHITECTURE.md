# Architecture

## Przegląd

Projekt jest lokalną aplikacją desktopową w Pythonie, docelowo uruchamianą na Raspberry Pi z ekranem HDMI.

Aplikacja używa:

- PySide6 do GUI, jeszcze niezaimplementowanego,
- SQLite do lokalnej bazy danych,
- czystej logiki domenowej w `core/`,
- adapterów sprzętowych w `hardware/`,
- kontrolerów i warstwy prezentacyjnej w `controller/`.

Główna zasada:

`core/` nie wie nic o GUI, bazie danych ani sprzęcie.

## Warstwy

`core/`

Logika domenowa: pieniądze, produkty, koszyk i zakończona sprzedaż. Ta warstwa operuje na modelach domenowych i liczbach całkowitych.

`data/`

SQLite, schemat bazy i repozytoria. Repozytoria mapują dane między SQLite a modelami domenowymi.

`hardware/`

Interfejs wagi i mock wagi. Przyszłe adaptery prawdziwego sprzętu powinny zostać w tej warstwie.

`controller/`

Fasada aplikacyjna dla GUI, obsługa komend, stan aplikacji oraz budowanie DTO/ViewState z gotowymi tekstami dla GUI.

`ui/`

Docelowe ekrany PySide6. UI ma renderować DTO/ViewState i wysyłać komendy/akcje do kontrolera. UI nie powinno importować modeli domenowych.

## Kierunek zależności

Dozwolone:

- `ui -> controller`
- `controller -> core`
- `controller -> data`
- `controller -> hardware`
- `data -> core`
- `hardware -> brak zależności od domeny` albo minimalnie do typów wspólnych, jeśli będzie to potrzebne

Niedozwolone:

- `core -> ui`
- `core -> data`
- `core -> hardware`
- `data -> ui`
- `hardware -> ui`
- `ui -> core`

## Aktualna struktura

```text
src/cash_assistant/
  main.py

  core/
    money.py
    product.py
    cart.py
    sale.py

  data/
    database.py
    product_repository.py
    sale_repository.py

  hardware/
    scale.py
    mock_scale.py

  controller/
    app_controller.py
    keyboard_controller.py
    labels.py
    view_state.py

  ui/
    formatters.py
    main_window.py
    sales_screen.py
    settings_screen.py
    history_screen.py
```

`main.py` oraz ekrany w `ui/` są jeszcze stubami przed implementacją PySide6.

## `core/`

### `money.py`

Odpowiedzialność:

- obliczenia na pieniądzach reprezentowanych jako `int` w groszach,
- liczenie wartości pozycji ważonej,
- liczenie wartości pozycji na sztuki,
- zaokrąglanie sumy do najbliższych 50 groszy,
- liczenie reszty.

`money.py` nie formatuje tekstów i nie parsuje tekstu użytkownika.

Aktualne funkcje:

- `calculate_weighted_line_total_grosze(unit_price_grosze, weight_grams)`
- `calculate_piece_line_total_grosze(unit_price_grosze, quantity)`
- `round_to_nearest_50_grosze(amount_grosze)`
- `calculate_change(paid_grosze, total_grosze)`

Zasady:

- pieniądze to zawsze `int` w groszach,
- waga to zawsze `int` w gramach,
- nie używać `float`,
- błędne wartości liczbowe zgłaszają `ValueError`.

### `product.py`

Model domenowy produktu:

- `Product`
- `UnitType.KG`
- `UnitType.PIECE`

Produkt ma:

- `id: int | None`
- `name: str`
- `unit_type: UnitType`
- `price_grosze: int`
- `active: bool`
- `sort_order: int`

### `cart.py`

Koszyk przechowuje bieżące pozycje sprzedaży.

`CartItem` jest snapshotem produktu:

- `product_id`
- `product_name_snapshot`
- `unit_type_snapshot`
- `unit_price_grosze_snapshot`
- `quantity_value`
- `line_total_grosze`

Dla `UnitType.KG` pole `quantity_value` oznacza gramy.

Dla `UnitType.PIECE` pole `quantity_value` oznacza liczbę sztuk.

### `sale.py`

`Sale` reprezentuje zakończoną sprzedaż. Powstaje z koszyka oraz kwoty otrzymanej od klienta.

`SaleItem` jest snapshotem pozycji koszyka. Zmiana produktu po sprzedaży nie zmienia historii sprzedaży.

## `data/`

`data/` odpowiada za SQLite i nie zawiera logiki GUI.

### `database.py`

Odpowiedzialność:

- otwieranie połączenia SQLite,
- inicjalizacja schematu,
- pomocniczy kontekst transakcji.

Tabele MVP:

- `products`
- `sales`
- `sale_items`

### `product_repository.py`

Repozytorium produktów obsługuje:

- listowanie aktywnych produktów,
- listowanie wszystkich produktów,
- odczyt produktu,
- tworzenie produktu,
- aktualizację produktu,
- dezaktywację produktu.

Repozytorium zwraca i przyjmuje modele domenowe, ponieważ należy do warstwy `data`, a nie do GUI.

### `sale_repository.py`

Repozytorium sprzedaży obsługuje:

- zapis sprzedaży,
- listę ostatnich sprzedaży,
- odczyt szczegółów sprzedaży.

Zapis sprzedaży jest transakcyjny. Jeśli zapis pozycji sprzedaży się nie powiedzie, rekord `sales` nie powinien zostać w bazie.

## `hardware/`

### `scale.py`

Definiuje abstrakcyjny interfejs:

- `get_weight_grams() -> int`
- `tare() -> None`

### `mock_scale.py`

Mock wagi używany w developmentcie i testach.

Umożliwia:

- ustawienie masy testowej w gramach,
- odczyt masy,
- tarowanie.

## `controller/`

`controller/` jest granicą między GUI a domeną.

### `app_controller.py`

`AppController` jest publiczną fasadą dla GUI.

Publiczne metody `AppController` nie powinny przyjmować ani zwracać modeli domenowych takich jak `Product`, `UnitType`, `Cart`, `CartItem`, `Sale` czy `SaleItem`.

Publiczne API:

- `list_products_for_settings() -> list[ProductListItemViewState]`
- `prepare_product_edit_view_state(product_id: int | None = None) -> ProductEditViewState`
- `save_product_from_input(product_input: ProductEditInput) -> ProductEditViewState`
- `select_product_by_id(product_id: int) -> ViewState`
- `add_selected_piece_product(quantity: int) -> ViewState`
- `remove_last_item() -> ViewState`
- `clear_cart() -> ViewState`
- `start_payment() -> ViewState`
- `cancel_current_operation() -> ViewState`
- `open_settings() -> ViewState`
- `open_history() -> ViewState`
- `set_paid_grosze(paid_grosze: int) -> PaymentState`
- `save_sale() -> SaleDetailsViewState`
- `list_sales_for_history(limit: int = 20) -> list[SaleSummaryViewState]`
- `read_sale_details(sale_id: int) -> SaleDetailsViewState | None`
- `prepare_view_state() -> ViewState`

Modele domenowe są używane tylko wewnątrz kontrolera i w repozytoriach.

### `keyboard_controller.py`

`KeyboardController` tłumaczy komendy klawiatury na akcje `AppController`.

`Command.SELECT_PRODUCT` przyjmuje `product_id`, nie `Product`.

Skróty numeryczne `1-9` są mapowane z pozycji produktu w `ProductViewState`, a nie traktowane jako `product_id`.

### `view_state.py`

Zawiera DTO/ViewState przygotowane dla GUI:

Sprzedaż:

- `ViewState`
- `ProductViewState`
- `CartItemViewState`
- `PaymentState`

Ustawienia produktów:

- `ProductListItemViewState`
- `ProductEditViewState`
- `ProductEditInput`
- `UnitOptionViewState`

Historia sprzedaży:

- `SaleSummaryViewState`
- `SaleDetailsViewState`
- `SaleItemViewState`

Buildery ViewState przygotowują gotowe teksty widoczne w GUI. GUI nie powinno formatować jednostek na podstawie `UnitType`.

### `labels.py`

Zawiera GUI-visible stałe tekstowe używane przez warstwę prezentacji:

- tekst waluty,
- teksty jednostek,
- statusy produktu,
- format daty,
- separatory tekstów prezentacyjnych.

Zasada: nowe napisy widoczne w GUI powinny trafiać do `controller/labels.py` albo innego jawnego modułu presentation, nie jako luźne literały w logice.

## `ui/`

`ui/` odpowiada za PySide6.

Aktualnie ekrany są stubami:

- `main_window.py`
- `sales_screen.py`
- `settings_screen.py`
- `history_screen.py`

Docelowo ekrany mają:

- renderować DTO/ViewState z `controller/`,
- wywoływać publiczne metody `AppController` albo komendy `KeyboardController`,
- nie importować `core.Product`, `core.UnitType`, `core.Sale`, `core.SaleItem`.

### `formatters.py`

Zawiera pomocnicze formatowanie prymitywów:

- `format_money`
- `format_weight_grams`
- `format_piece_quantity`
- `format_unit_price`

Nie importuje `core/`. Korzysta z tekstów z `controller/labels.py`.

## Testy

Aktualny zakres testów:

- `test_money.py` — obliczenia pieniędzy,
- `test_product.py` — model produktu,
- `test_cart.py` — koszyk,
- `test_sale.py` — zakończona sprzedaż,
- `test_database.py` — inicjalizacja bazy,
- `test_product_repository.py` — repozytorium produktów,
- `test_sale_repository.py` — repozytorium sprzedaży i transakcyjność,
- `test_scale.py` — interfejs i mock wagi,
- `test_formatters.py` — pomocnicze formatowanie UI,
- `test_view_state.py` — buildery ViewState,
- `test_app_controller.py` — publiczna fasada GUI,
- `test_keyboard_controller.py` — komendy klawiatury.

## Kolejny etap

Przed implementacją GUI architektura jest przygotowana do modelu:

```text
PySide6 screen -> AppController / KeyboardController -> ViewState DTO
```

GUI powinno pozostać cienką warstwą bez logiki sprzedaży.
