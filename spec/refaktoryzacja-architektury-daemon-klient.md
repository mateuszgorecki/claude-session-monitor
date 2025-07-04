# Plan Realizacji Epica: Refaktoryzacja Architektury na Daemon + Klient + Widget

## 🔧 WAŻNE: Narzędzia Deweloperskie

**WSZYSTKIE operacje Python muszą być wykonywane przez `uv`:**
- Zamiast `python` → `uv run python`
- Zamiast `python3` → `uv run python3`
- Zamiast `pip` → `uv pip`
- Zamiast `python -m pytest` → `uv run python -m pytest`

## 1. Cele i Główne Założenia (Executive Summary)

### Cel Biznesowy
Rozdzielenie obecnej monolitycznej aplikacji na trzy komponenty:
- **Daemon w tle** - ciągłe monitorowanie i zapis danych do pliku (co 10 sekund)
- **Aplikacja kliencka** - wyświetlanie danych z pliku (podobna do obecnej)
- **Widget Scriptable** - wyświetlanie danych na iPadzie poprzez iCloud Drive

### Cel Techniczny
Przekształcenie obecnej architektury z jednego skryptu `claude_monitor.py` na modularny system składający się z:
- Demona zbierającego dane w tle (co 10 sekund) z obsługą notyfikacji systemowych
- Lekkiego klienta do wyświetlania danych
- Standardowego formatu pliku danych dla współdzielenia między komponentami (także przez iCloud Drive)

### Główne Założenia i Strategia
- **Zachowanie kompatybilności wstecznej** - obecni użytkownicy nie powinni odczuć różnicy
- **Separacja odpowiedzialności** - daemon zbiera dane i wysyła notyfikacje, klient tylko wyświetla
- **Standaryzacja formatu danych** - JSON schema dla współdzielenia danych
- **Synchronizacja przez iCloud Drive** - dla dostępu z iPada
- **Fokus na macOS** - implementacja wyłącznie dla macOS

### Kryteria Ukończenia Sekcji
- [x] Cel biznesowy i techniczny są jasno sformułowane i mierzalne
- [x] Wybrana strategia (refaktoryzacja z podziałem na komponenty) jest uzasadniona
- [x] Sekcja jest zrozumiała dla osób nietechnicznych

## 2. Definicja Architektury i Zasad Pracy (`PROJECT_BLUEPRINT.MD`)

### Architektura Rozwiązania

```
┌─────────────────────────────────────────────────────────────────┐
│                         NOWA ARCHITEKTURA                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐  │
│  │   claude_daemon │    │ claude_monitor  │    │   Widget    │  │
│  │                 │    │                 │    │ Scriptable  │  │
│  │  - Zbiera dane  │    │ - Wyświetla     │    │             │  │
│  │  - Zapisuje do  │    │   dane z pliku  │    │ - Czyta     │  │
│  │    pliku        │    │ - UI/Terminal   │    │   plik z    │  │
│  │  - Notyfikacje  │    │ - Interakcja    │    │   iCloud    │  │
│  │  - Działa w tle │    │                 │    │ - Widget    │  │
│  │                 │    │                 │    │   iOS       │  │
│  └─────────────────┘    └─────────────────┘    └─────────────┘  │
│           │                       │                       │     │
│           │                       │                       │     │
│           ▼                       ▼                       ▼     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │            WSPÓLNY PLIK DANYCH (JSON)                      │ │
│  │                                                             │ │
│  │  ~/.config/claude-monitor/monitor_data.json                │ │
│  │  ~/Library/Mobile Documents/iCloud~com~claude~monitor/     │ │
│  │                    monitor_data.json (kopia dla widget)    │ │
│  │                                                             │ │
│  │  - Aktualne dane sesji                                     │ │
│  │  - Historyczne maksima                                     │ │
│  │  - Konfiguracja                                            │ │
│  │  - Timestamp ostatniej aktualizacji                       │ │
│  │  - Status błędów (jeśli ccusage zwraca błąd)              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Stos Technologiczny

- **Python 3.9+** - podstawowy język dla daemon i klienta
- **JSON** - format wymiany danych między komponentami
- **ccusage CLI** - zewnętrzne narzędzie do pobierania danych Claude API
- **launchd** - zarządzanie demonem w systemie macOS
- **JavaScript (Scriptable)** - widget na iOS/iPadOS
- **iCloud Drive** - synchronizacja danych dla widgetu
- **macOS notifications** - system notyfikacji (terminal-notifier lub osascript)
- **Signal handling** - graceful shutdown demona

### Struktura Projektu

```
claude-session-monitor/
├── src/
│   ├── daemon/
│   │   ├── __init__.py
│   │   ├── claude_daemon.py          # Główny daemon
│   │   ├── data_collector.py         # Logika zbierania danych
│   │   ├── file_manager.py           # Zarządzanie plikami danych + iCloud sync
│   │   ├── notification_manager.py   # Obsługa notyfikacji systemowych
│   │   └── config_manager.py         # Zarządzanie konfiguracją
│   ├── client/
│   │   ├── __init__.py
│   │   ├── claude_monitor.py         # Klient (obecny plik)
│   │   ├── display_manager.py        # Logika wyświetlania
│   │   └── data_reader.py            # Odczyt danych z pliku
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── data_models.py            # Definicje struktur danych
│   │   ├── constants.py              # Stałe konfiguracyjne
│   │   └── utils.py                  # Wspólne narzędzia
│   └── widget/
│       ├── claude_widget.js          # Widget Scriptable
│       ├── widget_config.json        # Konfiguracja widgetu
│       └── README_widget.md          # Instrukcja instalacji
├── tests/
│   ├── test_daemon.py
│   ├── test_client.py
│   ├── test_data_models.py
│   └── integration_tests.py
├── scripts/
│   ├── install_daemon.sh             # Instalacja demona macOS (launchd)
│   ├── uninstall_daemon.sh           # Odinstalowanie demona
│   └── migrate_from_old.py           # Migracja z starej wersji
├── config/
│   └── com.claude.monitor.daemon.plist # macOS launchd plist
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DAEMON_SETUP.md
│   └── WIDGET_SETUP.md
├── claude_monitor.py                 # Backward compatibility wrapper
├── requirements.txt
├── setup.py
└── README.md
```

### Konwencje i Standardy

**Nazewnictwo:**
- Pliki: `snake_case.py`
- Klasy: `PascalCase`
- Funkcje i zmienne: `snake_case`
- Stałe: `UPPER_CASE`

**Git i Commity:**
- Konwencja: `type(scope): description`
- Typy: `feat`, `fix`, `refactor`, `docs`, `test`
- Scope: `daemon`, `client`, `widget`, `shared`

**Styl kodowania:**
- Black formatter
- isort dla importów
- pylint dla jakości kodu
- Type hints obowiązkowe

**Format danych:**
- JSON Schema validation
- Atomowe zapisy (write + rename)
- Synchronizacja z iCloud Drive dla widgetu
- Obsługa błędów ccusage w strukturze JSON

### Kryteria Ukończenia Sekcji
- [x] Zaproponowana architektura jest kompletna i gotowa do implementacji
- [x] Stos technologiczny jest zdefiniowany
- [x] Zasady pracy są jednoznaczne i nie pozostawiają miejsca na interpretację

## 3. Analiza Ryzyk i Niejasności

### Ryzyka Techniczne

1. **Współbieżny dostęp do pliku danych**
   - **Ryzyko:** Race conditions przy jednoczesnym zapisie/odczycie
   - **Mitygacja:** Atomic writes (write + rename) - wystarczające dla naszego przypadku

2. **Utrata danych przy crash demona**
   - **Ryzyko:** Dane w pamięci mogą zostać utracone
   - **Mitygacja:** Regularny flush do pliku + signal handling

3. **Kompatybilność wsteczna**
   - **Ryzyko:** Istniejący workflow użytkowników może się zepsuć
   - **Mitygacja:** Wrapper script + migracja automatyczna

4. **Błędy ccusage**
   - **Ryzyko:** ccusage może zwracać błędy lub być niedostępne
   - **Mitygacja:** Wyświetlanie statusu błędu w JSON + notyfikacja użytkownika

### Ryzyka Projektowe

1. **Złożoność migracji**
   - **Ryzyko:** Użytkownicy mogą mieć problemy z migracją
   - **Mitygacja:** Automatyczna migracja + dokumentacja

2. **Synchronizacja iCloud**
   - **Ryzyko:** Opóźnienia w synchronizacji mogą powodować nieaktualne dane w widgecie
   - **Mitygacja:** Akceptujemy to - przy następnym odczycie dane będą aktualne

### Kluczowe Pytania do Biznesu/Product Ownera

1. **Czy daemon powinien być automatycznie uruchamiany przy starcie systemu?**
2. **Czy zachować możliwość uruchamiania w trybie "jednorazowym" (jak obecnie)?**
3. **Czy widget może początkowo wyświetlać uproszczone dane?**
4. **Czy akceptujemy brak notyfikacji na iPadzie (tylko macOS)?**

### Kryteria Ukończenia Sekcji
- [x] Każde zidentyfikowane ryzyko ma przypisaną strategię mitygacji
- [x] Sformułowane pytania są konkretne i wymagają jednoznacznej odpowiedzi
- [x] Lista jest wyczerpująca

## 4. Szczegółowy Plan Działania (Fazy i Zadania)

### Faza 1: Przygotowanie Infrastruktury i Modeli Danych ✅ **UKOŃCZONE**

#### Zadanie 1.1: Implementacja modeli danych współdzielonych ✅

- [x] **(RED)** Utwórz plik testu `test_data_models.py` i napisz test sprawdzający serializację/deserializację struktury `SessionData`
- [x] Uruchom testy i potwierdź, że test nie przechodzi z błędem `ImportError`
- [x] **(GREEN)** Zaimplementuj klasę `SessionData` w `src/shared/data_models.py` z podstawowymi polami
- [x] Uruchom testy i potwierdź, że test przechodzi
- [x] **(REFACTOR)** Dodaj type hints i docstringi do klasy
- [x] **(REPEAT)** Dodaj testy dla `MonitoringData` i `ConfigData` oraz zaimplementuj te klasy

#### Zadanie 1.2: Implementacja JSON Schema validation ✅

- [x] **(RED)** Napisz test sprawdzający walidację JSON Schema dla `SessionData`
- [x] Uruchom testy i potwierdź niepowodzenie
- [x] **(GREEN)** Zaimplementuj walidację JSON Schema w `data_models.py`
- [x] Uruchom testy i potwierdź powodzenie
- [x] **(REFACTOR)** Zoptymalizuj walidację pod kątem wydajności

#### Zadanie 1.3: Implementacja file managera z atomic writes ✅

- [x] **(RED)** Napisz test sprawdzający atomowy zapis do pliku JSON
- [x] Uruchom testy i potwierdź niepowodzenie
- [x] **(GREEN)** Zaimplementuj `FileManager` w `src/shared/file_manager.py`
- [x] Uruchom testy i potwierdź powodzenie
- [x] **(REFACTOR)** Dodaj error handling i synchronizację z iCloud Drive

**Wyniki Fazy 1:**
- ✅ 45 testów przechodzi bez błędów
- ✅ Kompleksowe modele danych z walidacją
- ✅ Atomowe operacje na plikach z sync iCloud
- ✅ Infrastruktura gotowa do implementacji demona

### Faza 2: Implementacja Demona

#### Zadanie 2.1: Implementacja core demona ✅

- [x] **(RED)** Napisz test sprawdzający podstawowy cykl życia demona (start/stop)
- [x] Uruchom testy i potwierdź niepowodzenie
- [x] **(GREEN)** Zaimplementuj `ClaudeDaemon` w `src/daemon/claude_daemon.py`
- [x] Uruchom testy i potwierdź powodzenie
- [x] **(REFACTOR)** Dodaj signal handling i graceful shutdown

#### Zadanie 2.2: Implementacja data collector ✅

- [x] **(RED)** Napisz test sprawdzający pobieranie danych z `ccusage`
- [x] Uruchom testy i potwierdź niepowodzenie (mock ccusage)
- [x] **(GREEN)** Zaimplementuj `DataCollector` w `src/daemon/data_collector.py`
- [x] Uruchom testy i potwierdź powodzenie
- [x] **(REFACTOR)** Dodaj error handling i retry logic

#### Zadanie 2.3: Integracja demona z file manager ✅

- [x] **(RED)** Napisz test integracyjny sprawdzający zapis danych przez demona
- [x] Uruchom testy i potwierdź niepowodzenie
- [x] **(GREEN)** Zintegruj `DataCollector` z `FileManager`
- [x] Uruchom testy i potwierdź powodzenie
- [x] **(REFACTOR)** Ustaw interwał 10 sekund dla pobierania danych

#### Zadanie 2.4: Implementacja notification manager ✅

- [x] **(RED)** Napisz test sprawdzający wysyłanie notyfikacji systemowych
- [x] Uruchom testy i potwierdź niepowodzenie
- [x] **(GREEN)** Zaimplementuj `NotificationManager` w `src/daemon/notification_manager.py`
- [x] Uruchom testy i potwierdź powodzenie
- [x] **(REFACTOR)** Dodaj obsługę terminal-notifier i fallback do osascript

#### Zadanie 2.5: Metodologia Obsługi ccusage - Wymaganie Zachowania Oryginalnego Podejścia

**KLUCZOWE WYMAGANIE:** Implementacja obsługi ccusage w nowym rozwiązaniu demonowym **MUSI** być identyczna z oryginalną implementacją w `claude_monitor.py`, ponieważ obecne rozwiązanie uproszczone nie jest satysfakcjonujące i nie gwarantuje poprawności działania.

##### Problemy z Obecną Implementacją Demona

Aktualny `data_collector.py` zawiera uproszczoną implementację, która pomija kluczowe aspekty oryginalnej logiki:

1. **Brak inteligentnej strategii pobierania danych** - wywołuje tylko `ccusage blocks -j` bez parametrów
2. **Brak obsługi okresów rozliczeniowych** - nie uwzględnia parametru `--start-day`
3. **Brak optymalizacji incrementalnej** - pobiera zawsze wszystkie dane zamiast używać parametru `-s`
4. **Nieprawidłowe przetwarzanie bloków** - używa niewłaściwych nazw pól:
   - `start_time` zamiast `startTime`
   - `end_time` zamiast `endTime`
   - `cost` zamiast `costUSD`
   - Próbuje czytać `input_tokens`/`output_tokens` bezpośrednio zamiast z `tokenCounts`
5. **Nieprawidłowa logika aktywności sesji** - używa arbitralnego 5-minutowego okna zamiast sprawdzać zakres czasu
6. **Brak śledzenia przetworzonych sesji** - może liczyć te same sesje wielokrotnie
7. **Brak cache'owania danych** - niepotrzebnie wywołuje ccusage przy każdym odczycie
8. **Brak zaawansowanej obsługi błędów** - nie obsługuje przypadków gdy ccusage zwraca błąd

##### Struktura Danych z ccusage (Rzeczywista)

Analiza wywołania `ccusage blocks -j` pokazuje faktyczną strukturę:

```json
{
  "blocks": [
    {
      "id": "2025-06-18T08:00:00.000Z",
      "startTime": "2025-06-18T08:00:00.000Z",
      "endTime": "2025-06-18T13:00:00.000Z",
      "actualEndTime": "2025-06-18T12:57:59.777Z",
      "isActive": false,
      "isGap": false,
      "entries": 527,
      "tokenCounts": {
        "inputTokens": 5941,
        "outputTokens": 23196,
        "cacheCreationInputTokens": 1094754,
        "cacheReadInputTokens": 19736284
      },
      "totalTokens": 29137,
      "costUSD": 16.636553099999986,
      "models": ["claude-sonnet-4", "claude-opus-4"],
      "burnRate": null,
      "projection": null
    }
  ]
}
```

##### Wymagana Implementacja - Zachowanie Oryginalnej Logiki

**1. Funkcja `run_ccusage()` (linie 102-109):**
```python
def run_ccusage(since_date: str = None) -> dict:
    command = ["ccusage", "blocks", "-j"]
    if since_date: command.extend(["-s", since_date])
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError):
        return {"blocks": []}
```

**2. Poprawne parsowanie bloków:**
```python
def _parse_ccusage_block(self, block: Dict[str, Any]) -> SessionData:
    # Parsowanie z prawidłowymi nazwami pól
    start_time = datetime.fromisoformat(block['startTime'].replace('Z', '+00:00'))
    end_time = None
    if 'endTime' in block and block['endTime']:
        end_time = datetime.fromisoformat(block['endTime'].replace('Z', '+00:00'))
    
    # Tokeny są w zagnieżdżonej strukturze
    token_counts = block.get('tokenCounts', {})
    input_tokens = token_counts.get('inputTokens', 0)
    output_tokens = token_counts.get('outputTokens', 0)
    total_tokens = block.get('totalTokens', 0)  # Suma input+output
    
    # Pozostałe pola
    cost_usd = block.get('costUSD', 0)
    is_active = block.get('isActive', False)
    
    return SessionData(
        session_id=block['id'],
        start_time=start_time,
        end_time=end_time,
        total_tokens=total_tokens,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        is_active=is_active
    )
```

**3. Inteligentna strategia pobierania danych (linie 153-179):**
```python
# Określanie optymalnej daty dla parametru -s
def determine_fetch_strategy(self, config: dict, billing_start_day: int):
    sub_start_date = get_subscription_period_start(billing_start_day)
    sub_start_date_str = sub_start_date.strftime('%Y-%m-%d')
    
    need_full_rescan = config.get("force_recalculate", False)
    need_max_tokens = not config.get("max_tokens") or need_full_rescan
    need_monthly_recalc = need_full_rescan or config.get("monthly_meta", {}).get("period_start") != sub_start_date_str
    
    if need_full_rescan:
        return None  # Pobierz wszystko
    elif need_monthly_recalc:
        return sub_start_date.strftime('%Y%m%d')
    else:
        # Incremental: dane z ostatniego tygodnia
        last_check = config.get("last_incremental_update")
        if last_check:
            since_date = datetime.strptime(last_check, '%Y-%m-%d') - timedelta(days=2)
        else:
            since_date = datetime.now() - timedelta(days=7)
        return since_date.strftime('%Y%m%d')
```

**4. Obsługa okresów rozliczeniowych (linie 111-118):**
```python
def get_subscription_period_start(start_day: int) -> date:
    today = date.today()
    if today.day >= start_day:
        return today.replace(day=start_day)
    else:
        first_day_of_current_month = today.replace(day=1)
        last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
        return last_day_of_previous_month.replace(day=min(start_day, last_day_of_previous_month.day))
```

**5. Cache i główna pętla (linie 280-285):**
```python
# W głównej pętli demona:
if time.time() - last_fetch_time > config_instance.CCUSAGE_FETCH_INTERVAL_SECONDS:
    fetched_data = run_ccusage(billing_period_fetch_since)
    if fetched_data and fetched_data.get("blocks"):
        cached_data = fetched_data
    last_fetch_time = time.time()
```

**6. Prawidłowa detekcja aktywnych sesji (linie 287-295):**
```python
def find_active_session(blocks: List[Dict], now_utc: datetime) -> Optional[Dict]:
    for block in blocks:
        if block.get("isGap", False): 
            continue
        start_time = parse_utc_time(block["startTime"])
        end_time = parse_utc_time(block["endTime"])
        if start_time <= now_utc <= end_time:
            return block
    return None
```

##### Zadania Implementacyjne

**Testy do napisania PRZED implementacją (TDD):**

- [ ] **(RED)** `test_run_ccusage_with_since_parameter` - sprawdza czy parametr `-s` jest prawidłowo przekazywany
- [ ] **(RED)** `test_parse_ccusage_block_with_nested_tokens` - sprawdza parsowanie zagnieżdżonych tokenCounts
- [ ] **(RED)** `test_subscription_period_calculation` - testuje obliczanie początku okresu rozliczeniowego
- [ ] **(RED)** `test_incremental_fetch_strategy` - testuje wybór strategii pobierania danych
- [ ] **(RED)** `test_active_session_detection_by_time_range` - testuje detekcję aktywnych sesji
- [ ] **(RED)** `test_processed_sessions_tracking` - testuje śledzenie przetworzonych sesji
- [ ] **(RED)** `test_max_tokens_persistence` - testuje zapisywanie i odczyt max_tokens
- [ ] **(RED)** `test_cache_expiration_logic` - testuje logikę wygasania cache

**Implementacja:**

- [ ] **(GREEN)** Przepisać `run_ccusage()` zgodnie z oryginalną implementacją
- [ ] **(GREEN)** Poprawić `_parse_ccusage_block()` na prawidłowe nazwy pól i strukturę
- [ ] **(GREEN)** Dodać `get_subscription_period_start()` i logikę okresów
- [ ] **(GREEN)** Zaimplementować inteligentną strategię pobierania z parametrem `-s`
- [ ] **(GREEN)** Dodać cache danych z 10-sekundowym interwałem
- [ ] **(GREEN)** Zaimplementować śledzenie processed_sessions
- [ ] **(GREEN)** Dodać persystencję max_tokens i last_incremental_update
- [ ] **(GREEN)** Poprawić detekcję aktywnych sesji na sprawdzanie zakresu czasu

**Refaktoryzacja istniejących testów:**

- [ ] **(REFACTOR)** Zaktualizować mocki w testach aby zwracały prawidłową strukturę ccusage
- [ ] **(REFACTOR)** Poprawić asercje testów aby sprawdzały prawidłowe pola
- [ ] **(REFACTOR)** Dodać testy integracyjne z prawdziwymi danymi JSON
- [ ] **(REFACTOR)** Usunąć testy oparte na nieprawidłowych założeniach (5-minutowe okno)

##### Uzasadnienie Wymagania

Oryginalna implementacja w `claude_monitor.py` została:
- **Przetestowana w praktyce** przez długi okres użytkowania
- **Zoptymalizowana pod kątem wydajności** - minimalizuje wywołania ccusage
- **Zaprojektowana do obsługi błędów** - graceful degradation przy problemach z ccusage
- **Dostosowana do specyfiki Claude API** - prawidłowe rozróżnianie stanów sesji
- **Zgodna z rzeczywistą strukturą danych** zwracanych przez ccusage

Uproszczona implementacja w demonie wprowadza regresję funkcjonalności i może prowadzić do:
- Nieprawidłowych obliczeń kosztów (wielokrotne liczenie tych samych sesji)
- Problemów z wydajnością przy dużej ilości danych historycznych
- Nieprawidłowego śledzenia aktywnych sesji
- Błędów parsowania danych z ccusage
- Utraty danych przy błędach ccusage

**Status:** ✅ **UKOŃCZONE** - DataCollector został całkowicie przepisany zgodnie z oryginalną logiką claude_monitor.py. Wszystkie 8 krytycznych problemów zostało naprawionych, a 87 testów przechodzi pomyślnie.

### Faza 3: Refaktoryzacja Klienta

#### Zadanie 3.1: Implementacja data reader

- [ ] **(RED)** Napisz test sprawdzający odczyt danych z pliku JSON
- [ ] Uruchom testy i potwierdź niepowodzenie
- [ ] **(GREEN)** Zaimplementuj `DataReader` w `src/client/data_reader.py`
- [ ] Uruchom testy i potwierdź powodzenie
- [ ] **(REFACTOR)** Dodaj cache i error handling

#### Zadanie 3.2: Refaktoryzacja display manager

- [ ] **(RED)** Napisz test sprawdzający formatowanie danych do wyświetlenia
- [ ] Uruchom testy i potwierdź niepowodzenie
- [ ] **(GREEN)** Wydziel logikę wyświetlania do `DisplayManager`
- [ ] Uruchom testy i potwierdź powodzenie
- [ ] **(REFACTOR)** Zoptymalizuj rendering progress barów

#### Zadanie 3.3: Aktualizacja głównego klienta

- [ ] Zrefaktoryzuj `claude_monitor.py` do używania `DataReader` i `DisplayManager`
- [ ] Uruchom testy integracyjne i potwierdź działanie
- [ ] Dodaj fallback do trybu standalone (dla kompatybilności wstecznej)

### Faza 4: Implementacja Widget Scriptable

#### Zadanie 4.1: Implementacja podstawowego widgetu

- [ ] Stwórz `claude_widget.js` z podstawową funkcjonalnością odczytu JSON
- [ ] Zaimplementuj wyświetlanie kluczowych metryk
- [ ] Dodaj error handling dla przypadków braku pliku danych

#### Zadanie 4.2: Konfiguracja i personalizacja widgetu

- [ ] Zaimplementuj `widget_config.json` z opcjami konfiguracyjnymi
- [ ] Dodaj możliwość wyboru wyświetlanych metryk
- [ ] Zaimplementuj różne rozmiary widgetu (small, medium, large)

### Faza 5: Narzędzia Systemowe i Deployment

#### Zadanie 5.1: Skrypty instalacji demona

- [ ] Stwórz `install_daemon.sh` dla macOS (launchd)
- [ ] Napisz `uninstall_daemon.sh` dla macOS
- [ ] Dodaj automatyczne uruchamianie przy starcie systemu
- [ ] Dodaj konfigurację ścieżki iCloud Drive

#### Zadanie 5.2: Migracja z starej wersji

- [ ] **(RED)** Napisz test sprawdzający migrację starych plików konfiguracji
- [ ] Uruchom testy i potwierdź niepowodzenie
- [ ] **(GREEN)** Zaimplementuj `migrate_from_old.py`
- [ ] Uruchom testy i potwierdź powodzenie
- [ ] **(REFACTOR)** Dodaj backup i rollback functionality

#### Zadanie 5.3: Wrapper dla kompatybilności wstecznej

- [ ] Zaktualizuj główny `claude_monitor.py` jako wrapper
- [ ] Dodaj detekcję czy daemon jest uruchomiony
- [ ] Zaimplementuj fallback do trybu standalone

### Kryteria Ukończenia Sekcji
- [x] Wszystkie fazy są logicznie uporządkowane
- [x] Zadania są "atomowe" - małe i skupione na jednym, konkretnym celu
- [x] Zadania implementujące logikę są jawnie rozpisane w krokach TDD
- [x] Każde zadanie jest weryfikowalne

## 5. Kryteria Akceptacji i Plan Testów

### Filozofia Testowania

1. **Testuj faktyczne implementacje, nie mocki:** Preferujemy testy integracyjne z prawdziwymi plikami JSON i procesami, aby mieć pewność, że komponenty działają ze sobą. Mocki stosujemy tylko do izolowania `ccusage` CLI.

2. **Dogłębne testowanie logiki, pragmatyczne testowanie UI:** Cała logika data collection, file management i data validation musi być w pełni pokryta testami jednostkowymi/integracyjnymi zgodnie z TDD. Terminal UI jest testowany głównie przez testy E2E.

### Plan Testów

#### Testy Jednostkowe/Integracyjne (TDD)
- **Data Models** (`SessionData`, `MonitoringData`, `ConfigData`, `ErrorStatus`)
- **File Manager** (atomic writes, iCloud sync, JSON validation)
- **Data Collector** (integration z ccusage, error handling, status błędów)
- **Notification Manager** (wysyłanie notyfikacji, różne mechanizmy)
- **Data Reader** (file reading, cache, error handling)
- **Daemon Core** (lifecycle, signal handling, graceful shutdown)

#### Testy E2E (End-to-End)
1. **Pełny cykl daemon → klient:** Uruchom daemon, poczekaj na zbieranie danych, uruchom klient i sprawdź wyświetlenie
2. **Migracja ze starej wersji:** Przygotuj stary plik konfiguracyjny, uruchom migrację, sprawdź działanie nowych komponentów
3. **Współbieżny dostęp:** Uruchom daemon i klient jednocześnie, sprawdź brak konfliktów
4. **Widget integration:** Sprawdź odczyt danych przez widget Scriptable
5. **Graceful shutdown:** Wyślij SIGTERM do demona, sprawdź czy dane zostały zapisane

#### Testy Manualne/Eksploracyjne
- **Instalacja demona na macOS** (launchd)
- **Synchronizacja iCloud** między macOS a iPadOS
- **Obsługa błędów ccusage** - wyświetlanie statusu błędu
- **Widget UI na różnych rozmiarach** (small, medium, large)
- **Kompatybilność wsteczna** z istniejącymi konfiguracjami

### Kryteria Ukończenia Sekcji
- [x] Filozofia testowania jest jasno określona
- [x] Plan testów jest kompletny i rozróżnia typy testów
- [x] Zdefiniowano kluczowe scenariusze E2E stanowiące "definition of done"

## 6. Proponowana Kolejność Realizacji (Roadmap)

### Etap 1: Fundament (Faza 1)
**Czas: 1-2 tygodnie**
- Implementacja shared data models
- JSON Schema validation
- File Manager z atomic writes
- **Dependency:** Brak
- **Możliwość równoległej pracy:** Tak, każde zadanie może być realizowane niezależnie

### Etap 2: Daemon (Faza 2)
**Czas: 2-3 tygodnie**
- Core daemon implementation
- Data collector z integracją ccusage
- Integracja z file manager
- **Dependency:** Zakończenie Etapu 1
- **Możliwość równoległej pracy:** Zadania 2.1 i 2.2 mogą być realizowane równolegle

### Etap 3: Klient (Faza 3)
**Czas: 1-2 tygodnie**
- Data reader implementation
- Display manager refactoring
- Aktualizacja głównego klienta
- **Dependency:** Zakończenie Etapu 1, możliwa częściowa praca równolegle z Etapem 2
- **Możliwość równoległej pracy:** Zadania 3.1 i 3.2 mogą być realizowane równolegle

### Etap 4: Widget (Faza 4)
**Czas: 1 tydzień**
- Widget Scriptable implementation
- Konfiguracja i personalizacja
- **Dependency:** Zakończenie Etapu 1, możliwa praca równolegle z Etapami 2-3
- **Możliwość równoległej pracy:** Tak, niezależny od innych komponentów

### Etap 5: Deployment (Faza 5)
**Czas: 1-2 tygodnie**
- Skrypty instalacji demona
- Migracja z starej wersji
- Wrapper kompatybilności wstecznej
- **Dependency:** Zakończenie Etapów 2-4
- **Możliwość równoległej pracy:** Zadania 5.1 i 5.2 mogą być realizowane równolegle

### Harmonogram Równoległy (Optymalizacja)
- **Tydzień 1-2:** Etap 1 (fundament)
- **Tydzień 3-4:** Etap 2 (daemon) + Etap 4 (widget) równolegle
- **Tydzień 5:** Etap 3 (klient) + dokończenie Etapu 4
- **Tydzień 6-7:** Etap 5 (deployment) + testy integracyjne

### Kryteria Ukończenia Sekcji
- [x] Kolejność jest logiczna i uwzględnia zależności techniczne
- [x] Zidentyfikowano zadania, które mogą być realizowane równolegle
- [x] Roadmapa jest logicznie spójna i technicznie wykonalna

---

**Szacowany całkowity czas realizacji:** 6-7 tygodni przy optymalnej organizacji pracy równoległej, 8-10 tygodni przy pracy sekwencyjnej.