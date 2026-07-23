# Cash Assistant

Pomocnicza aplikacja sprzedażowa na Raspberry Pi do obsługi sprzedaży warzyw i owoców.

Aplikacja ma działać lokalnie, offline, z ekranem HDMI oraz obsługą przez GUI i skróty klawiaturowe. Docelowo może współpracować z wagą elektroniczną, ale na etapie developmentu używany jest `MockScale`.

## Aktualny stan

Zaimplementowane:

- logika pieniędzy, produktów, koszyka i sprzedaży w `core/`,
- SQLite schema i repozytoria w `data/`,
- walidowana i transakcyjna synchronizacja produktów z `config/products.csv`,
- transakcyjny zapis sprzedaży,
- interfejs wagi i mock wagi,
- `AppController` jako publiczna fasada dla GUI,
- `KeyboardController`,
- GUI PySide6 ekranu sprzedaży,
- DTO/ViewState dla sprzedaży i historii sprzedaży,
- ikony produktów z `assets/products`,
- centralne etykiety GUI-visible w `controller/labels.py`,
- testy automatyczne.

Jeszcze niezaimplementowane:

- docelowy wygląd ekranu sprzedaży,
- udostępnienie ekranu historii w głównej nawigacji,
- adapter prawdziwej wagi.

## Najważniejsze zasady

- Pieniądze są reprezentowane jako `int` w groszach.
- Waga jest reprezentowana jako `int` w gramach.
- Nie używać `float` do pieniędzy.
- `core/` nie importuje `ui/`, `data/`, `hardware/` ani `controller/`.
- GUI ma korzystać z `AppController`, `KeyboardController` i DTO/ViewState.
- GUI nie powinno importować modeli domenowych z `core/`.
- Produkty są zarządzane przez `config/products.csv`, nie przez GUI.
- Brak produktu w CSV nie usuwa go z SQLite; ukrycie wymaga `active=false`.
- Teksty widoczne w GUI trzymamy w warstwie `controller/presentation`, obecnie w `controller/labels.py` i ViewState.

## Dokumentacja

- [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Komendy developerskie

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check .
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy src
```
