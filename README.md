# Cash Assistant

Pomocnicza aplikacja sprzedażowa na Raspberry Pi do obsługi sprzedaży warzyw i owoców.

Aplikacja ma działać lokalnie, offline, z ekranem HDMI oraz obsługą przez GUI i skróty klawiaturowe. Docelowo może współpracować z wagą elektroniczną, ale na etapie developmentu używany jest `MockScale`.

## Aktualny stan

Zaimplementowane:

- logika pieniędzy, produktów, koszyka i sprzedaży w `core/`,
- SQLite schema i repozytoria w `data/`,
- transakcyjny zapis sprzedaży,
- interfejs wagi i mock wagi,
- `AppController` jako publiczna fasada dla GUI,
- `KeyboardController`,
- DTO/ViewState dla sprzedaży, ustawień produktów i historii sprzedaży,
- centralne etykiety GUI-visible w `controller/labels.py`,
- testy automatyczne.

Jeszcze niezaimplementowane:

- ekrany PySide6,
- uruchamialny bootstrap aplikacji w `main.py`,
- adapter prawdziwej wagi.

## Najważniejsze zasady

- Pieniądze są reprezentowane jako `int` w groszach.
- Waga jest reprezentowana jako `int` w gramach.
- Nie używać `float` do pieniędzy.
- `core/` nie importuje `ui/`, `data/`, `hardware/` ani `controller/`.
- GUI ma korzystać z `AppController`, `KeyboardController` i DTO/ViewState.
- GUI nie powinno importować modeli domenowych z `core/`.
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
