# Plan Realizacji Epica: Refaktoryzacja Architektury na Daemon + Klient + Widget

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

#### Zadanie 2.3: Integracja demona z file manager

- [ ] **(RED)** Napisz test integracyjny sprawdzający zapis danych przez demona
- [ ] Uruchom testy i potwierdź niepowodzenie
- [ ] **(GREEN)** Zintegruj `DataCollector` z `FileManager`
- [ ] Uruchom testy i potwierdź powodzenie
- [ ] **(REFACTOR)** Ustaw interwał 10 sekund dla pobierania danych

#### Zadanie 2.4: Implementacja notification manager

- [ ] **(RED)** Napisz test sprawdzający wysyłanie notyfikacji systemowych
- [ ] Uruchom testy i potwierdź niepowodzenie
- [ ] **(GREEN)** Zaimplementuj `NotificationManager` w `src/daemon/notification_manager.py`
- [ ] Uruchom testy i potwierdź powodzenie
- [ ] **(REFACTOR)** Dodaj obsługę terminal-notifier i fallback do osascript

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