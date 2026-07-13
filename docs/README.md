# Dokumentacja projektu

Ten katalog zawiera aktualny opis wymagań i architektury aplikacji Cash Assistant.

## Pliki

- [REQUIREMENTS.md](./REQUIREMENTS.md) — wymagania funkcjonalne i niefunkcjonalne.
- [ARCHITECTURE.md](./ARCHITECTURE.md) — aktualny podział warstw, zależności, DTO i zasady implementacji.

## Aktualny stan projektu

Zaimplementowane są:

- logika domenowa w `core/`,
- SQLite i repozytoria w `data/`,
- interfejs wagi i `MockScale` w `hardware/`,
- fasada `AppController` dla GUI,
- `KeyboardController`,
- DTO/ViewState dla sprzedaży, ustawień produktów i historii,
- centralne etykiety GUI-visible w `controller/labels.py`,
- testy jednostkowe i integracyjne bez PySide6.

Jeszcze niezaimplementowane są:

- właściwe ekrany PySide6,
- uruchamialny start aplikacji w `main.py`,
- adapter prawdziwej wagi.

## Zasada dla GUI

GUI ma być cienką warstwą:

```text
PySide6 screen -> AppController / KeyboardController -> ViewState DTO
```

GUI nie powinno importować modeli domenowych z `core/`.

## Walidacja

Standardowy zestaw kontroli:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check .
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy src
```
